// PROJECT VOXELCORE — simple, low-contention job system.
// A fixed pool of workers pulls tasks from a shared mutex+condvar queue.
// Designed for coarse tasks (chunk gen, meshing), not fork-join micro-tasks.
// Predictable latency beats theoretical throughput: no spinning, no thread oversubscription.
#pragma once

#include <condition_variable>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>
#include <atomic>
#include <algorithm>

namespace vc {

class JobSystem {
public:
    explicit JobSystem(std::size_t workers = 0) {
        const std::size_t hw = std::thread::hardware_concurrency();
        const std::size_t n = workers ? workers : (hw > 1 ? hw - 1 : 1);
        start(n);
    }
    ~JobSystem() { shutdown(); }

    JobSystem(const JobSystem&) = delete;
    JobSystem& operator=(const JobSystem&) = delete;

    std::size_t workerCount() const { return workers_.size(); }

    void submit(std::function<void()> job) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            queue_.push_back(std::move(job));
            ++pending_;
        }
        cv_.notify_one();
    }

    // Wait until every currently-queued job started through this pool is done.
    void waitIdle() {
        std::unique_lock<std::mutex> lock(mutex_);
        idleCv_.wait(lock, [&] { return pending_ == 0; });
    }

    std::uint64_t completedTasks() const { return completed_.load(std::memory_order_relaxed); }

    // Parallel-for over [0, count) in batches of `grain`. The calling thread participates.
    // Blocks until all batches are done. Unrelated jobs in the pool are not waited on.
    void parallelFor(std::size_t count, std::size_t grain, const std::function<void(std::size_t)>& fn) {
        if (count == 0) return;
        grain = std::max<std::size_t>(1, grain);
        const std::size_t batches = (count + grain - 1) / grain;
        if (batches == 1 || workers_.empty()) {
            for (std::size_t i = 0; i < count; ++i) fn(i);
            return;
        }
        std::atomic<std::size_t> next{0};
        std::atomic<std::size_t> finished{0};
        const std::size_t helpers = std::min(batches - 1, workers_.size());
        const std::size_t totalParticipants = helpers + 1;
        std::mutex doneMutex;
        std::condition_variable doneCv;
        auto run = [&] {
            for (;;) {
                const std::size_t b = next.fetch_add(1, std::memory_order_relaxed);
                if (b >= batches) break;
                const std::size_t begin = b * grain, end = std::min(count, begin + grain);
                for (std::size_t i = begin; i < end; ++i) fn(i);
            }
            if (finished.fetch_add(1, std::memory_order_acq_rel) + 1 == totalParticipants) {
                std::lock_guard<std::mutex> lock(doneMutex);
                doneCv.notify_all();
            }
        };
        for (std::size_t k = 0; k < helpers; ++k) submit(run);
        run();
        std::unique_lock<std::mutex> lock(doneMutex);
        doneCv.wait(lock, [&] { return finished.load(std::memory_order_acquire) == totalParticipants; });
    }

    void shutdown() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (stopping_) return;
            stopping_ = true;
        }
        cv_.notify_all();
        for (auto& t : workers_) if (t.joinable()) t.join();
        workers_.clear();
    }

private:
    void start(std::size_t n) {
        stopping_ = false;
        for (std::size_t i = 0; i < n; ++i) {
            workers_.emplace_back([this] {
                for (;;) {
                    std::function<void()> job;
                    {
                        std::unique_lock<std::mutex> lock(mutex_);
                        cv_.wait(lock, [&] { return stopping_ || !queue_.empty(); });
                        if (stopping_ && queue_.empty()) return;
                        job = std::move(queue_.front());
                        queue_.pop_front();
                    }
                    job();
                    {
                        std::lock_guard<std::mutex> lock(mutex_);
                        --pending_;
                        completed_.fetch_add(1, std::memory_order_relaxed);
                        if (pending_ == 0) idleCv_.notify_all();
                    }
                }
            });
        }
    }

    std::vector<std::thread> workers_;
    std::deque<std::function<void()>> queue_;
    std::mutex mutex_;
    std::condition_variable cv_, idleCv_;
    std::size_t pending_ = 0;
    bool stopping_ = false;
    std::atomic<std::uint64_t> completed_{0};
};

} // namespace vc
