// PROJECT VOXELCORE — NBT (Named Binary Tag) read/write, Java Edition format.
// Big-endian, tag-typed. Supports the full tag set used by region files.
// This is a from-scratch implementation written against the format's public documentation
// (wiki.vg/NBT) — clean-room, no code copied.
#pragma once

#include <cstdint>
#include <cstring>
#include <memory>
#include <string>
#include <vector>
#include <array>
#include <variant>
#include <stdexcept>
#include <algorithm>

namespace vc::nbt {

enum TagType : std::uint8_t {
    End = 0, Byte = 1, Short = 2, Int = 3, Long = 4, Float = 5, Double = 6,
    ByteArray = 7, String = 8, List = 9, Compound = 10, IntArray = 11, LongArray = 12,
};

struct Value;
using NbtList = std::vector<Value>;
using NbtCompound = std::vector<std::pair<std::string, Value>>;
using NbtByteArray = std::vector<std::int8_t>;
using NbtIntArray = std::vector<std::int32_t>;
using NbtLongArray = std::vector<std::int64_t>;

using ValueData = std::variant<std::monostate, std::int8_t, std::int16_t, std::int32_t, std::int64_t,
                               float, double, NbtByteArray, std::string, NbtList, NbtCompound, NbtIntArray, NbtLongArray>;

struct Value {
    TagType type = End;
    ValueData data;

    Value() : type(End), data(std::monostate{}) {}
    explicit Value(std::int8_t v) : type(Byte), data(v) {}
    explicit Value(std::int16_t v) : type(Short), data(v) {}
    explicit Value(std::int32_t v) : type(Int), data(v) {}
    explicit Value(std::int64_t v) : type(Long), data(v) {}
    explicit Value(float v) : type(Float), data(v) {}
    explicit Value(double v) : type(Double), data(v) {}
    explicit Value(NbtByteArray v) : type(ByteArray), data(std::move(v)) {}
    explicit Value(std::string v) : type(String), data(std::move(v)) {}
    Value(TagType listType, NbtList v) : type(List), data(std::move(v)) { (void)listType; }
    explicit Value(NbtCompound v) : type(Compound), data(std::move(v)) {}
    explicit Value(NbtIntArray v) : type(IntArray), data(std::move(v)) {}
    explicit Value(NbtLongArray v) : type(LongArray), data(std::move(v)) {}

    static Value compound() { return Value(NbtCompound{}); }
    static Value list(TagType elem, NbtList items = {}) { return Value(elem, std::move(items)); }

    bool isCompound() const { return type == Compound; }
    bool isList() const { return type == List; }
    const NbtCompound* asCompound() const { return std::get_if<NbtCompound>(&data); }
    const NbtList* asList() const { return std::get_if<NbtList>(&data); }

    const Value* find(const std::string& key) const {
        const NbtCompound* c = asCompound();
        if (!c) return nullptr;
        for (const auto& [k, v] : *c) if (k == key) return &v;
        return nullptr;
    }
    Value& put(NbtCompound& c, const std::string& key, Value v) {
        for (auto& [k, val] : c) if (k == key) { val = std::move(v); return val; }
        c.emplace_back(key, std::move(v));
        return c.back().second;
    }
};

// --- writers ---
class Writer {
public:
    void writeByte(std::uint8_t b) { out_.push_back(b); }
    void writeBytes(const std::uint8_t* p, std::size_t n) { out_.insert(out_.end(), p, p + n); }
    void writeU16(std::uint16_t v) { writeBE<std::uint16_t>(v); }
    void writeU32(std::uint32_t v) { writeBE<std::uint32_t>(v); }
    void writeU64(std::uint64_t v) { writeBE<std::uint64_t>(v); }
    void writeF32(float v) { std::uint32_t u; std::memcpy(&u, &v, 4); writeU32(u); }
    void writeF64(double v) { std::uint64_t u; std::memcpy(&u, &v, 8); writeU64(u); }

    void writeString(const std::string& s) {
        writeU16(static_cast<std::uint16_t>(s.size()));
        writeBytes(reinterpret_cast<const std::uint8_t*>(s.data()), s.size());
    }

    void writePayload(const Value& v) {
        switch (v.type) {
            case Byte: writeByte(static_cast<std::uint8_t>(std::get<std::int8_t>(v.data))); break;
            case Short: writeU16(static_cast<std::uint16_t>(std::get<std::int16_t>(v.data))); break;
            case Int: writeU32(static_cast<std::uint32_t>(std::get<std::int32_t>(v.data))); break;
            case Long: writeU64(static_cast<std::uint64_t>(std::get<std::int64_t>(v.data))); break;
            case Float: writeF32(std::get<float>(v.data)); break;
            case Double: writeF64(std::get<double>(v.data)); break;
            case ByteArray: {
                const auto& a = std::get<NbtByteArray>(v.data);
                writeU32(static_cast<std::uint32_t>(a.size()));
                writeBytes(reinterpret_cast<const std::uint8_t*>(a.data()), a.size());
                break; }
            case String: writeString(std::get<std::string>(v.data)); break;
            case List: {
                const auto& items = std::get<NbtList>(v.data);
                const TagType elem = items.empty() ? End : items.front().type;
                writeByte(static_cast<std::uint8_t>(elem));
                writeU32(static_cast<std::uint32_t>(items.size()));
                for (const auto& item : items) writePayload(item);
                break; }
            case Compound: {
                const auto& c = std::get<NbtCompound>(v.data);
                for (const auto& [k, val] : c) {
                    writeByte(static_cast<std::uint8_t>(val.type));
                    writeString(k);
                    writePayload(val);
                }
                writeByte(End);
                break; }
            case IntArray: {
                const auto& a = std::get<NbtIntArray>(v.data);
                writeU32(static_cast<std::uint32_t>(a.size()));
                for (std::int32_t x : a) writeU32(static_cast<std::uint32_t>(x));
                break; }
            case LongArray: {
                const auto& a = std::get<NbtLongArray>(v.data);
                writeU32(static_cast<std::uint32_t>(a.size()));
                for (std::int64_t x : a) writeU64(static_cast<std::uint64_t>(x));
                break; }
            case End: break;
        }
    }

    // Top-level named tag (as stored inside region files).
    void writeNamedRoot(const std::string& name, const Value& v) {
        writeByte(static_cast<std::uint8_t>(v.type));
        writeString(name);
        writePayload(v);
    }

    const std::vector<std::uint8_t>& bytes() const { return out_; }
    std::vector<std::uint8_t> take() { return std::move(out_); }

private:
    template <typename T> void writeBE(T v) {
        std::uint8_t buf[sizeof(T)];
        for (std::size_t i = 0; i < sizeof(T); ++i) buf[sizeof(T) - 1 - i] = static_cast<std::uint8_t>((v >> (i * 8)) & 0xFF);
        writeBytes(buf, sizeof(T));
    }
    std::vector<std::uint8_t> out_;
};

// --- reader ---
class Reader {
public:
    Reader(const std::uint8_t* data, std::size_t size) : data_(data), size_(size) {}

    std::uint8_t readByte() { need(1); return data_[pos_++]; }
    std::uint16_t readU16() { return readBE<std::uint16_t>(); }
    std::uint32_t readU32() { return readBE<std::uint32_t>(); }
    std::uint64_t readU64() { return readBE<std::uint64_t>(); }
    float readF32() { std::uint32_t u = readU32(); float f; std::memcpy(&f, &u, 4); return f; }
    double readF64() { std::uint64_t u = readU64(); double d; std::memcpy(&d, &u, 8); return d; }
    std::string readString() {
        const std::uint16_t n = readU16();
        need(n);
        std::string s(reinterpret_cast<const char*>(data_ + pos_), n);
        pos_ += n;
        return s;
    }

    Value readPayload(TagType type) {
        switch (type) {
            case Byte: return Value(static_cast<std::int8_t>(readByte()));
            case Short: return Value(static_cast<std::int16_t>(readU16()));
            case Int: return Value(static_cast<std::int32_t>(readU32()));
            case Long: return Value(static_cast<std::int64_t>(readU64()));
            case Float: return Value(readF32());
            case Double: return Value(readF64());
            case ByteArray: {
                const std::uint32_t n = readU32(); need(n);
                NbtByteArray a(n);
                std::memcpy(a.data(), data_ + pos_, n); pos_ += n;
                return Value(std::move(a)); }
            case String: return Value(readString());
            case List: {
                const TagType elem = static_cast<TagType>(readByte());
                const std::uint32_t n = readU32();
                NbtList items; items.reserve(n);
                for (std::uint32_t i = 0; i < n; ++i) items.push_back(readPayload(elem));
                return Value(elem, std::move(items)); }
            case Compound: {
                NbtCompound c;
                for (;;) {
                    const TagType t = static_cast<TagType>(readByte());
                    if (t == End) break;
                    std::string k = readString();
                    c.emplace_back(std::move(k), readPayload(t));
                }
                return Value(std::move(c)); }
            case IntArray: {
                const std::uint32_t n = readU32();
                NbtIntArray a(n);
                for (std::uint32_t i = 0; i < n; ++i) a[i] = static_cast<std::int32_t>(readU32());
                return Value(std::move(a)); }
            case LongArray: {
                const std::uint32_t n = readU32();
                NbtLongArray a(n);
                for (std::uint32_t i = 0; i < n; ++i) a[i] = static_cast<std::int64_t>(readU64());
                return Value(std::move(a)); }
            case End: return Value{};
        }
        throw std::runtime_error("nbt: unknown tag type");
    }

    // Returns (name, value) of the top-level named tag.
    std::pair<std::string, Value> readNamedRoot() {
        const TagType t = static_cast<TagType>(readByte());
        std::string name = readString();
        return {std::move(name), readPayload(t)};
    }

    std::size_t remaining() const { return size_ - pos_; }

private:
    void need(std::size_t n) const { if (pos_ + n > size_) throw std::runtime_error("nbt: truncated data"); }
    template <typename T> T readBE() {
        need(sizeof(T));
        T v = 0;
        for (std::size_t i = 0; i < sizeof(T); ++i) v = static_cast<T>((v << 8) | data_[pos_ + i]);
        pos_ += sizeof(T);
        return v;
    }
    const std::uint8_t* data_;
    std::size_t size_;
    std::size_t pos_ = 0;
};

} // namespace vc::nbt
