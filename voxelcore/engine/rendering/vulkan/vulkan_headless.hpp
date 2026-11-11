// PROJECT VOXELCORE — headless Vulkan renderer (no window, direct-to-image).
//
// Compile-verified everywhere Vulkan-Headers are available; RUNTIME-verified only where a
// Vulkan driver exists (CI uses Mesa lavapipe; real hardware preferred). Never used as a
// substitute for a windowed swapchain renderer — it exists so the real GPU path
// (shaders, pipeline, memory, draw) is exercised end-to-end in CI and on dev machines.
//
// Draw path: RGBA8 color attachment + D32 depth, single graphics pipeline, push constants
// carry the view-projection matrix, no descriptors (uniforms are push constants;
// vertex attributes are position/color only).
#pragma once

#if !defined(VOXELCORE_WITH_VULKAN)
#error "vulkan_headless.hpp requires VOXELCORE_WITH_VULKAN (CMake option VOXELCORE_WITH_VULKAN=ON)"
#endif

#include <vulkan/vulkan.h>
#include "../math.hpp"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <vector>
#include <string>
#include <algorithm>

namespace vc::vk {

struct VulkanError : std::runtime_error { using std::runtime_error::runtime_error; };

#define VC_VK_TRY(expr, what)                                                          \
    do {                                                                               \
        const VkResult _r = (expr);                                                    \
        if (_r != VK_SUCCESS)                                                          \
            throw VulkanError(std::string(what) + " failed (VkResult=" + std::to_string(_r) + ")"); \
    } while (0)

struct Vertex { float x, y, z, r, g, b, a; };

class HeadlessRenderer {
public:
    HeadlessRenderer(uint32_t width, uint32_t height, std::string spvDir)
        : width_(width), height_(height), spvDir_(std::move(spvDir)) {}

    ~HeadlessRenderer() { destroy(); }
    HeadlessRenderer(const HeadlessRenderer&) = delete;
    HeadlessRenderer& operator=(const HeadlessRenderer&) = delete;

    void init() {
        // --- instance ---
        VkApplicationInfo appInfo{}; appInfo.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
        appInfo.pApplicationName = "voxelcore-headless";
        appInfo.applicationVersion = VK_MAKE_VERSION(0, 1, 0);
        appInfo.pEngineName = "voxelcore";
        appInfo.engineVersion = VK_MAKE_VERSION(0, 1, 0);
        appInfo.apiVersion = VK_API_VERSION_1_2;
        VkInstanceCreateInfo instInfo{}; instInfo.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
        instInfo.pApplicationInfo = &appInfo;
        VC_VK_TRY(vkCreateInstance(&instInfo, nullptr, &instance_), "vkCreateInstance");

        // --- physical device with a graphics queue ---
        uint32_t deviceCount = 0;
        vkEnumeratePhysicalDevices(instance_, &deviceCount, nullptr);
        if (deviceCount == 0) throw VulkanError("no Vulkan physical device found (driver missing?)");
        std::vector<VkPhysicalDevice> devices(deviceCount);
        vkEnumeratePhysicalDevices(instance_, &deviceCount, devices.data());
        // Prefer discrete, then integrated, then anything (lavapipe = CPU type).
        auto score = [](const VkPhysicalDeviceProperties& p) {
            switch (p.deviceType) {
                case VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU: return 3;
                case VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU: return 2;
                case VK_PHYSICAL_DEVICE_TYPE_CPU: return 1;
                default: return 0;
            }
        };
        int best = -1; uint32_t bestScore = 0;
        for (uint32_t i = 0; i < deviceCount; ++i) {
            VkPhysicalDeviceProperties props{};
            vkGetPhysicalDeviceProperties(devices[i], &props);
            // Need a graphics-capable queue family.
            uint32_t qfCount = 0;
            vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &qfCount, nullptr);
            std::vector<VkQueueFamilyProperties> qfs(qfCount);
            vkGetPhysicalDeviceQueueFamilyProperties(devices[i], &qfCount, qfs.data());
            uint32_t graphicsFamily = VK_QUEUE_FAMILY_IGNORED;
            for (uint32_t q = 0; q < qfCount; ++q) {
                if (qfs[q].queueFlags & VK_QUEUE_GRAPHICS_BIT) { graphicsFamily = q; break; }
            }
            if (graphicsFamily == VK_QUEUE_FAMILY_IGNORED) continue;
            const uint32_t s = score(props);
            if (best < 0 || s > bestScore) { best = static_cast<int>(i); bestScore = s; graphicsFamily_ = graphicsFamily; }
        }
        if (best < 0) throw VulkanError("no graphics-capable Vulkan device found");
        physicalDevice_ = devices[static_cast<std::size_t>(best)];
        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(physicalDevice_, &props);
        std::fprintf(stderr, "vulkan: using device '%s' (type %d)\n", props.deviceName, props.deviceType);

        float queuePriority = 1.0f;
        VkDeviceQueueCreateInfo queueInfo{}; queueInfo.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queueInfo.queueFamilyIndex = graphicsFamily_;
        queueInfo.queueCount = 1;
        queueInfo.pQueuePriorities = &queuePriority;
        VkPhysicalDeviceFeatures features{};
        VkDeviceCreateInfo devInfo{}; devInfo.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        devInfo.queueCreateInfoCount = 1;
        devInfo.pQueueCreateInfos = &queueInfo;
        devInfo.pEnabledFeatures = &features;
        VC_VK_TRY(vkCreateDevice(physicalDevice_, &devInfo, nullptr, &device_), "vkCreateDevice");
        vkGetDeviceQueue(device_, graphicsFamily_, 0, &queue_);

        // --- command pool ---
        VkCommandPoolCreateInfo poolInfo{}; poolInfo.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        poolInfo.queueFamilyIndex = graphicsFamily_;
        poolInfo.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        VC_VK_TRY(vkCreateCommandPool(device_, &poolInfo, nullptr, &commandPool_), "vkCreateCommandPool");

        // --- images: color (R8G8B8A8_UNORM, TRANSFER_SRC) + depth ---
        colorImage_ = createImage(VK_FORMAT_R8G8B8A8_UNORM,
                                  VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                                  VK_IMAGE_ASPECT_COLOR_BIT);
        depthImage_ = createImage(VK_FORMAT_D32_SFLOAT,
                                  VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
                                  VK_IMAGE_ASPECT_DEPTH_BIT);

        // --- render pass ---
        VkAttachmentDescription colorAttachment{};
        colorAttachment.format = VK_FORMAT_R8G8B8A8_UNORM;
        colorAttachment.samples = VK_SAMPLE_COUNT_1_BIT;
        colorAttachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        colorAttachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        colorAttachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        colorAttachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        colorAttachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        colorAttachment.finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        VkAttachmentDescription depthAttachment{};
        depthAttachment.format = VK_FORMAT_D32_SFLOAT;
        depthAttachment.samples = VK_SAMPLE_COUNT_1_BIT;
        depthAttachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        depthAttachment.storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depthAttachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        depthAttachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        depthAttachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        depthAttachment.finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;
        VkAttachmentReference colorRef{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
        VkAttachmentReference depthRef{1, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &colorRef;
        subpass.pDepthStencilAttachment = &depthRef;
        VkSubpassDependency dependency{};
        dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
        dependency.dstSubpass = 0;
        dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT | VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT | VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
        dependency.srcAccessMask = 0;
        dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT | VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;
        VkAttachmentDescription attachments[2] = {colorAttachment, depthAttachment};
        VkRenderPassCreateInfo rpInfo{}; rpInfo.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        rpInfo.attachmentCount = 2;
        rpInfo.pAttachments = attachments;
        rpInfo.subpassCount = 1;
        rpInfo.pSubpasses = &subpass;
        rpInfo.dependencyCount = 1;
        rpInfo.pDependencies = &dependency;
        VC_VK_TRY(vkCreateRenderPass(device_, &rpInfo, nullptr, &renderPass_), "vkCreateRenderPass");

        // --- framebuffer ---
        VkImageView attachmentsView[2] = {colorImage_.view, depthImage_.view};
        VkFramebufferCreateInfo fbInfo{}; fbInfo.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        fbInfo.renderPass = renderPass_;
        fbInfo.attachmentCount = 2;
        fbInfo.pAttachments = attachmentsView;
        fbInfo.width = width_;
        fbInfo.height = height_;
        fbInfo.layers = 1;
        VC_VK_TRY(vkCreateFramebuffer(device_, &fbInfo, nullptr, &framebuffer_), "vkCreateFramebuffer");

        // --- graphics pipeline ---
        createPipeline();

        // --- command buffer ---
        VkCommandBufferAllocateInfo cmdInfo{}; cmdInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        cmdInfo.commandPool = commandPool_;
        cmdInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cmdInfo.commandBufferCount = 1;
        VC_VK_TRY(vkAllocateCommandBuffers(device_, &cmdInfo, &commandBuffer_), "vkAllocateCommandBuffers");

        VkFenceCreateInfo fenceInfo{}; fenceInfo.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        fenceInfo.flags = VK_FENCE_CREATE_SIGNALED_BIT;
        VC_VK_TRY(vkCreateFence(device_, &fenceInfo, nullptr, &fence_), "vkCreateFence");
    }

    // Draws `vertices`/`indices` with the given view-projection and writes a binary PPM.
    void renderToPpm(const std::vector<Vertex>& vertices, const std::vector<std::uint32_t>& indices,
                     const math::Mat4& viewProj, const char* ppmPath) {
        if (vertices.empty() || indices.empty()) throw VulkanError("nothing to draw");
        createBuffers(vertices, indices);
        recordAndSubmit(viewProj, indices.size());
        readBackAndWritePpm(ppmPath);
    }

private:
    struct ImageBundle { VkImage image = VK_NULL_HANDLE; VkDeviceMemory memory = VK_NULL_HANDLE; VkImageView view = VK_NULL_HANDLE; };

    uint32_t findMemoryType(uint32_t typeBits, VkMemoryPropertyFlags properties) const {
        VkPhysicalDeviceMemoryProperties memProps{};
        vkGetPhysicalDeviceMemoryProperties(physicalDevice_, &memProps);
        for (uint32_t i = 0; i < memProps.memoryTypeCount; ++i)
            if ((typeBits & (1u << i)) && (memProps.memoryTypes[i].propertyFlags & properties) == properties) return i;
        throw VulkanError("no suitable memory type");
    }

    ImageBundle createImage(VkFormat format, VkImageUsageFlags usage, VkImageAspectFlags aspect) {
        ImageBundle b;
        VkImageCreateInfo imgInfo{}; imgInfo.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
        imgInfo.imageType = VK_IMAGE_TYPE_2D;
        imgInfo.format = format;
        imgInfo.extent = {width_, height_, 1};
        imgInfo.mipLevels = 1;
        imgInfo.arrayLayers = 1;
        imgInfo.samples = VK_SAMPLE_COUNT_1_BIT;
        imgInfo.tiling = VK_IMAGE_TILING_OPTIMAL;
        imgInfo.usage = usage;
        imgInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        imgInfo.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        VC_VK_TRY(vkCreateImage(device_, &imgInfo, nullptr, &b.image), "vkCreateImage");
        VkMemoryRequirements req{};
        vkGetImageMemoryRequirements(device_, b.image, &req);
        VkMemoryAllocateInfo alloc{}; alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        alloc.allocationSize = req.size;
        alloc.memoryTypeIndex = findMemoryType(req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        VC_VK_TRY(vkAllocateMemory(device_, &alloc, nullptr, &b.memory), "vkAllocateMemory(image)");
        VC_VK_TRY(vkBindImageMemory(device_, b.image, b.memory, 0), "vkBindImageMemory");
        VkImageViewCreateInfo viewInfo{}; viewInfo.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        viewInfo.image = b.image;
        viewInfo.viewType = VK_IMAGE_VIEW_TYPE_2D;
        viewInfo.format = format;
        viewInfo.subresourceRange.aspectMask = aspect;
        viewInfo.subresourceRange.levelCount = 1;
        viewInfo.subresourceRange.layerCount = 1;
        VC_VK_TRY(vkCreateImageView(device_, &viewInfo, nullptr, &b.view), "vkCreateImageView");
        return b;
    }

    VkBuffer createBuffer(VkDeviceSize size, VkBufferUsageFlags usage, VkMemoryPropertyFlags properties, VkDeviceMemory& outMemory) {
        VkBufferCreateInfo bufInfo{}; bufInfo.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        bufInfo.size = size;
        bufInfo.usage = usage;
        bufInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        VkBuffer buffer = VK_NULL_HANDLE;
        VC_VK_TRY(vkCreateBuffer(device_, &bufInfo, nullptr, &buffer), "vkCreateBuffer");
        VkMemoryRequirements req{};
        vkGetBufferMemoryRequirements(device_, buffer, &req);
        VkMemoryAllocateInfo alloc{}; alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        alloc.allocationSize = req.size;
        alloc.memoryTypeIndex = findMemoryType(req.memoryTypeBits, properties);
        VC_VK_TRY(vkAllocateMemory(device_, &alloc, nullptr, &outMemory), "vkAllocateMemory(buffer)");
        VC_VK_TRY(vkBindBufferMemory(device_, buffer, outMemory, 0), "vkBindBufferMemory");
        return buffer;
    }

    void createBuffers(const std::vector<Vertex>& vertices, const std::vector<std::uint32_t>& indices) {
        destroyBuffers();
        vertexBuffer_ = createBuffer(vertices.size() * sizeof(Vertex), VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                                     VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, vertexMemory_);
        indexBuffer_ = createBuffer(indices.size() * sizeof(std::uint32_t), VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
                                    VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, indexMemory_);
        void* data = nullptr;
        VC_VK_TRY(vkMapMemory(device_, vertexMemory_, 0, vertices.size() * sizeof(Vertex), 0, &data), "vkMapMemory(vertex)");
        std::memcpy(data, vertices.data(), vertices.size() * sizeof(Vertex));
        vkUnmapMemory(device_, vertexMemory_);
        VC_VK_TRY(vkMapMemory(device_, indexMemory_, 0, indices.size() * sizeof(std::uint32_t), 0, &data), "vkMapMemory(index)");
        std::memcpy(data, indices.data(), indices.size() * sizeof(std::uint32_t));
        vkUnmapMemory(device_, indexMemory_);
        // Readback buffer.
        readbackBuffer_ = createBuffer(static_cast<VkDeviceSize>(width_) * height_ * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                                       VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, readbackMemory_);
    }

    static std::vector<std::uint32_t> readSpv(const std::string& path) {
        std::ifstream f(path, std::ios::binary | std::ios::ate);
        if (!f) throw VulkanError("cannot open SPIR-V: " + path + " (build-time glslangValidator missing?)");
        const std::streamsize size = f.tellg();
        f.seekg(0);
        std::vector<std::uint32_t> words(static_cast<std::size_t>(size) / 4);
        f.read(reinterpret_cast<char*>(words.data()), size);
        return words;
    }

    void createPipeline() {
        const auto vert = readSpv(spvDir_ + "/voxelcore.vert.spv");
        const auto frag = readSpv(spvDir_ + "/voxelcore.frag.spv");
        VkShaderModule vertModule = createShaderModule(vert);
        VkShaderModule fragModule = createShaderModule(frag);
        VkPipelineShaderStageCreateInfo stages[2]{};
        stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vertModule;
        stages[0].pName = "main";
        stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = fragModule;
        stages[1].pName = "main";

        VkVertexInputBindingDescription binding{};
        binding.binding = 0;
        binding.stride = sizeof(Vertex);
        binding.inputRate = VK_VERTEX_INPUT_RATE_VERTEX;
        VkVertexInputAttributeDescription attributes[2]{};
        attributes[0] = {0, 0, VK_FORMAT_R32G32B32_SFLOAT, 0};
        attributes[1] = {1, 0, VK_FORMAT_R32G32B32A32_SFLOAT, offsetof(Vertex, r)};
        VkPipelineVertexInputStateCreateInfo vertexInput{}; vertexInput.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
        vertexInput.vertexBindingDescriptionCount = 1;
        vertexInput.pVertexBindingDescriptions = &binding;
        vertexInput.vertexAttributeDescriptionCount = 2;
        vertexInput.pVertexAttributeDescriptions = attributes;

        VkPipelineInputAssemblyStateCreateInfo inputAssembly{}; inputAssembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
        inputAssembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

        VkViewport viewport{0, 0, static_cast<float>(width_), static_cast<float>(height_), 0.0f, 1.0f};
        VkRect2D scissor{{0, 0}, {width_, height_}};
        VkPipelineViewportStateCreateInfo viewportState{}; viewportState.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
        viewportState.viewportCount = 1;
        viewportState.pViewports = &viewport;
        viewportState.scissorCount = 1;
        viewportState.pScissors = &scissor;

        VkPipelineRasterizationStateCreateInfo raster{}; raster.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
        raster.polygonMode = VK_POLYGON_MODE_FILL;
        raster.cullMode = VK_CULL_MODE_NONE; // winding unaudited; enable BACK after GPU validation
        raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
        raster.lineWidth = 1.0f;

        VkPipelineMultisampleStateCreateInfo multisample{}; multisample.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
        multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

        VkPipelineDepthStencilStateCreateInfo depthStencil{}; depthStencil.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
        depthStencil.depthTestEnable = VK_TRUE;
        depthStencil.depthWriteEnable = VK_TRUE;
        depthStencil.depthCompareOp = VK_COMPARE_OP_LESS;

        VkPipelineColorBlendAttachmentState blendAttachment{};
        blendAttachment.colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT | VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
        VkPipelineColorBlendStateCreateInfo colorBlend{}; colorBlend.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
        colorBlend.attachmentCount = 1;
        colorBlend.pAttachments = &blendAttachment;

        VkPushConstantRange pushRange{};
        pushRange.stageFlags = VK_SHADER_STAGE_VERTEX_BIT;
        pushRange.offset = 0;
        pushRange.size = sizeof(float) * 16;
        VkPipelineLayoutCreateInfo layoutInfo{}; layoutInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
        layoutInfo.pushConstantRangeCount = 1;
        layoutInfo.pPushConstantRanges = &pushRange;
        VC_VK_TRY(vkCreatePipelineLayout(device_, &layoutInfo, nullptr, &pipelineLayout_), "vkCreatePipelineLayout");

        VkGraphicsPipelineCreateInfo pipelineInfo{}; pipelineInfo.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
        pipelineInfo.stageCount = 2;
        pipelineInfo.pStages = stages;
        pipelineInfo.pVertexInputState = &vertexInput;
        pipelineInfo.pInputAssemblyState = &inputAssembly;
        pipelineInfo.pViewportState = &viewportState;
        pipelineInfo.pRasterizationState = &raster;
        pipelineInfo.pMultisampleState = &multisample;
        pipelineInfo.pDepthStencilState = &depthStencil;
        pipelineInfo.pColorBlendState = &colorBlend;
        pipelineInfo.layout = pipelineLayout_;
        pipelineInfo.renderPass = renderPass_;
        pipelineInfo.subpass = 0;
        VC_VK_TRY(vkCreateGraphicsPipelines(device_, VK_NULL_HANDLE, 1, &pipelineInfo, nullptr, &pipeline_), "vkCreateGraphicsPipelines");
        vkDestroyShaderModule(device_, vertModule, nullptr);
        vkDestroyShaderModule(device_, fragModule, nullptr);
    }

    VkShaderModule createShaderModule(const std::vector<std::uint32_t>& words) {
        VkShaderModuleCreateInfo info{}; info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        info.codeSize = words.size() * sizeof(std::uint32_t);
        info.pCode = words.data();
        VkShaderModule module = VK_NULL_HANDLE;
        VC_VK_TRY(vkCreateShaderModule(device_, &info, nullptr, &module), "vkCreateShaderModule");
        return module;
    }

    void recordAndSubmit(const math::Mat4& viewProj, std::size_t indexCount) {
        // Wait for any previous frame.
        VC_VK_TRY(vkWaitForFences(device_, 1, &fence_, VK_TRUE, UINT64_MAX), "vkWaitForFences");
        VC_VK_TRY(vkResetFences(device_, 1, &fence_), "vkResetFences");
        VC_VK_TRY(vkResetCommandBuffer(commandBuffer_, 0), "vkResetCommandBuffer");

        VkCommandBufferBeginInfo beginInfo{}; beginInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        beginInfo.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        VC_VK_TRY(vkBeginCommandBuffer(commandBuffer_, &beginInfo), "vkBeginCommandBuffer");

        VkClearValue clearValues[2]{};
        clearValues[0].color = {{0.35f, 0.55f, 0.85f, 1.0f}}; // sky
        clearValues[1].depthStencil = {1.0f, 0};
        VkRenderPassBeginInfo rpBegin{}; rpBegin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        rpBegin.renderPass = renderPass_;
        rpBegin.framebuffer = framebuffer_;
        rpBegin.renderArea.extent = {width_, height_};
        rpBegin.clearValueCount = 2;
        rpBegin.pClearValues = clearValues;
        vkCmdBeginRenderPass(commandBuffer_, &rpBegin, VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(commandBuffer_, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline_);
        VkBuffer vertexBuffers[] = {vertexBuffer_};
        VkDeviceSize offsets[] = {0};
        vkCmdBindVertexBuffers(commandBuffer_, 0, 1, vertexBuffers, offsets);
        vkCmdBindIndexBuffer(commandBuffer_, indexBuffer_, 0, VK_INDEX_TYPE_UINT32);
        vkCmdPushConstants(commandBuffer_, pipelineLayout_, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(float) * 16, viewProj.data());
        vkCmdDrawIndexed(commandBuffer_, static_cast<uint32_t>(indexCount), 1, 0, 0, 0);
        vkCmdEndRenderPass(commandBuffer_);

        // Copy image to the readback buffer.
        VkBufferImageCopy region{};
        region.bufferRowLength = width_;
        region.bufferImageHeight = height_;
        region.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        region.imageSubresource.layerCount = 1;
        region.imageExtent = {width_, height_, 1};
        vkCmdCopyImageToBuffer(commandBuffer_, colorImage_.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, readbackBuffer_, 1, &region);

        VC_VK_TRY(vkEndCommandBuffer(commandBuffer_), "vkEndCommandBuffer");
        VkSubmitInfo submit{}; submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &commandBuffer_;
        VC_VK_TRY(vkQueueSubmit(queue_, 1, &submit, fence_), "vkQueueSubmit");
        VC_VK_TRY(vkWaitForFences(device_, 1, &fence_, VK_TRUE, UINT64_MAX), "vkQueueSubmit(wait)");
    }

    void readBackAndWritePpm(const char* path) {
        void* data = nullptr;
        VC_VK_TRY(vkMapMemory(device_, readbackMemory_, 0, static_cast<VkDeviceSize>(width_) * height_ * 4, 0, &data), "vkMapMemory(readback)");
        std::FILE* f = std::fopen(path, "wb");
        if (!f) { vkUnmapMemory(device_, readbackMemory_); throw VulkanError(std::string("cannot write ") + path); }
        std::fprintf(f, "P6\n%u %u\n255\n", width_, height_);
        const std::uint8_t* px = static_cast<const std::uint8_t*>(data);
        for (std::size_t i = 0; i < static_cast<std::size_t>(width_) * height_; ++i) {
            const std::uint8_t rgb[3] = {px[i * 4 + 0], px[i * 4 + 1], px[i * 4 + 2]}; // RGBA
            std::fwrite(rgb, 1, 3, f);
        }
        std::fclose(f);
        vkUnmapMemory(device_, readbackMemory_);
    }

    void destroyBuffers() {
        if (indexBuffer_) vkDestroyBuffer(device_, indexBuffer_, nullptr);
        if (indexMemory_) vkFreeMemory(device_, indexMemory_, nullptr);
        if (vertexBuffer_) vkDestroyBuffer(device_, vertexBuffer_, nullptr);
        if (vertexMemory_) vkFreeMemory(device_, vertexMemory_, nullptr);
        if (readbackBuffer_) vkDestroyBuffer(device_, readbackBuffer_, nullptr);
        if (readbackMemory_) vkFreeMemory(device_, readbackMemory_, nullptr);
        indexBuffer_ = vertexBuffer_ = readbackBuffer_ = VK_NULL_HANDLE;
        indexMemory_ = vertexMemory_ = readbackMemory_ = VK_NULL_HANDLE;
    }

    void destroy() {
        if (!device_) return;
        vkDeviceWaitIdle(device_);
        destroyBuffers();
        if (fence_) vkDestroyFence(device_, fence_, nullptr);
        if (commandBuffer_) vkFreeCommandBuffers(device_, commandPool_, 1, &commandBuffer_);
        if (framebuffer_) vkDestroyFramebuffer(device_, framebuffer_, nullptr);
        if (pipeline_) vkDestroyPipeline(device_, pipeline_, nullptr);
        if (pipelineLayout_) vkDestroyPipelineLayout(device_, pipelineLayout_, nullptr);
        if (renderPass_) vkDestroyRenderPass(device_, renderPass_, nullptr);
        vkDestroyImageView(device_, colorImage_.view, nullptr);
        vkDestroyImage(device_, colorImage_.image, nullptr);
        vkFreeMemory(device_, colorImage_.memory, nullptr);
        vkDestroyImageView(device_, depthImage_.view, nullptr);
        vkDestroyImage(device_, depthImage_.image, nullptr);
        vkFreeMemory(device_, depthImage_.memory, nullptr);
        if (commandPool_) vkDestroyCommandPool(device_, commandPool_, nullptr);
        vkDestroyDevice(device_, nullptr);
        if (instance_) vkDestroyInstance(instance_, nullptr);
        device_ = VK_NULL_HANDLE;
        instance_ = VK_NULL_HANDLE;
    }

    uint32_t width_, height_;
    std::string spvDir_;
    VkInstance instance_ = VK_NULL_HANDLE;
    VkPhysicalDevice physicalDevice_ = VK_NULL_HANDLE;
    uint32_t graphicsFamily_ = 0;
    VkDevice device_ = VK_NULL_HANDLE;
    VkQueue queue_ = VK_NULL_HANDLE;
    VkCommandPool commandPool_ = VK_NULL_HANDLE;
    VkCommandBuffer commandBuffer_ = VK_NULL_HANDLE;
    VkFence fence_ = VK_NULL_HANDLE;
    ImageBundle colorImage_, depthImage_;
    VkRenderPass renderPass_ = VK_NULL_HANDLE;
    VkFramebuffer framebuffer_ = VK_NULL_HANDLE;
    VkPipelineLayout pipelineLayout_ = VK_NULL_HANDLE;
    VkPipeline pipeline_ = VK_NULL_HANDLE;
    VkBuffer vertexBuffer_ = VK_NULL_HANDLE, indexBuffer_ = VK_NULL_HANDLE, readbackBuffer_ = VK_NULL_HANDLE;
    VkDeviceMemory vertexMemory_ = VK_NULL_HANDLE, indexMemory_ = VK_NULL_HANDLE, readbackMemory_ = VK_NULL_HANDLE;
};

} // namespace vc::vk
