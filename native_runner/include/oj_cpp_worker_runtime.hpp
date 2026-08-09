#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif

#include <windows.h>
#include <psapi.h>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace oj_cpp_runtime {

using json = nlohmann::json;

struct Digest128 {
    std::uint64_t high = 0;
    std::uint64_t low = 0;

    void xor_with(const Digest128& other) {
        high ^= other.high;
        low ^= other.low;
    }

    std::string hex() const {
        std::ostringstream stream;
        stream << std::hex << std::setfill('0') << std::setw(16) << high
               << std::setw(16) << low;
        return stream.str();
    }
};

#pragma pack(push, 1)
struct StoreHeader {
    char magic[8];
    std::uint32_t version;
    std::uint64_t count;
    std::uint64_t table_offset;
    std::uint64_t payload_start;
};

struct IndexEntryV1 {
    std::uint64_t offset;
    std::uint64_t length;
};

struct IndexEntryV2 {
    std::uint64_t offset;
    std::uint64_t length;
    unsigned char expected_digest[16];
    unsigned char flags;
    unsigned char reserved[7];
};
#pragma pack(pop)

static_assert(sizeof(StoreHeader) == 36, "unexpected .ojbin header layout");
static_assert(sizeof(IndexEntryV1) == 16, "unexpected .ojbin v1 index layout");
static_assert(sizeof(IndexEntryV2) == 40, "unexpected .ojbin v2 index layout");

inline std::wstring utf8_to_wide(const std::string& value) {
    if (value.empty()) return std::wstring();
    const int size = MultiByteToWideChar(
        CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
        static_cast<int>(value.size()), nullptr, 0);
    if (size <= 0) throw std::runtime_error("invalid UTF-8 path");
    std::wstring result(static_cast<std::size_t>(size), L'\0');
    if (MultiByteToWideChar(
            CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
            static_cast<int>(value.size()), result.data(), size) != size) {
        throw std::runtime_error("failed to convert UTF-8 path");
    }
    return result;
}

inline std::uint64_t read_big_endian_u64(const unsigned char* bytes) {
    std::uint64_t value = 0;
    for (int index = 0; index < 8; ++index) {
        value = (value << 8u) | bytes[index];
    }
    return value;
}

struct CaseRecord {
    json value;
    std::optional<Digest128> expected_digest;
};

class MappedCaseStore {
public:
    explicit MappedCaseStore(const std::string& path) {
        const std::wstring wide_path = utf8_to_wide(path);
        file_ = CreateFileW(
            wide_path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
            OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file_ == INVALID_HANDLE_VALUE) {
            throw std::runtime_error("cannot open case store");
        }
        LARGE_INTEGER size;
        if (!GetFileSizeEx(file_, &size) || size.QuadPart < 0) {
            close();
            throw std::runtime_error("cannot read case-store size");
        }
        size_ = static_cast<std::uint64_t>(size.QuadPart);
        mapping_ = CreateFileMappingW(file_, nullptr, PAGE_READONLY, 0, 0, nullptr);
        if (!mapping_) {
            close();
            throw std::runtime_error("cannot create case-store mapping");
        }
        data_ = static_cast<const unsigned char*>(
            MapViewOfFile(mapping_, FILE_MAP_READ, 0, 0, 0));
        if (!data_) {
            close();
            throw std::runtime_error("cannot map case store");
        }
        validate_header();
    }

    MappedCaseStore(const MappedCaseStore&) = delete;
    MappedCaseStore& operator=(const MappedCaseStore&) = delete;

    ~MappedCaseStore() { close(); }

    std::uint64_t size() const { return header_.count; }

    CaseRecord read(std::uint64_t index) const {
        if (index >= header_.count) throw std::out_of_range("case index");
        std::uint64_t offset = 0;
        std::uint64_t length = 0;
        std::optional<Digest128> expected_digest;
        if (header_.version == 1) {
            IndexEntryV1 entry;
            const std::uint64_t position =
                header_.table_offset + index * sizeof(IndexEntryV1);
            std::memcpy(&entry, data_ + position, sizeof(entry));
            offset = entry.offset;
            length = entry.length;
        } else {
            IndexEntryV2 entry;
            const std::uint64_t position =
                header_.table_offset + index * sizeof(IndexEntryV2);
            std::memcpy(&entry, data_ + position, sizeof(entry));
            offset = entry.offset;
            length = entry.length;
            if ((entry.flags & 1u) != 0u) {
                expected_digest = Digest128{
                    read_big_endian_u64(entry.expected_digest),
                    read_big_endian_u64(entry.expected_digest + 8)};
            }
        }
        if (offset < sizeof(StoreHeader) || length > header_.table_offset ||
            offset > header_.table_offset - length) {
            throw std::runtime_error("case points outside payload section");
        }
        const char* begin = reinterpret_cast<const char*>(data_ + offset);
        const char* end = begin + length;
        return CaseRecord{json::parse(begin, end), expected_digest};
    }

private:
    void validate_header() {
        if (size_ < sizeof(StoreHeader)) {
            throw std::runtime_error("case store is truncated");
        }
        std::memcpy(&header_, data_, sizeof(header_));
        if (std::memcmp(header_.magic, "OJBIN001", 8) != 0) {
            throw std::runtime_error("invalid case-store magic");
        }
        if (header_.version != 1 && header_.version != 2) {
            throw std::runtime_error("unsupported case-store version");
        }
        if (header_.payload_start != sizeof(StoreHeader) ||
            header_.table_offset > size_) {
            throw std::runtime_error("invalid case-store offsets");
        }
        const std::uint64_t entry_size =
            header_.version == 1 ? sizeof(IndexEntryV1) : sizeof(IndexEntryV2);
        if (header_.count > (size_ - header_.table_offset) / entry_size) {
            throw std::runtime_error("case-store index is truncated");
        }
    }

    void close() noexcept {
        if (data_) UnmapViewOfFile(data_);
        if (mapping_) CloseHandle(mapping_);
        if (file_ != INVALID_HANDLE_VALUE) CloseHandle(file_);
        data_ = nullptr;
        mapping_ = nullptr;
        file_ = INVALID_HANDLE_VALUE;
    }

    HANDLE file_ = INVALID_HANDLE_VALUE;
    HANDLE mapping_ = nullptr;
    const unsigned char* data_ = nullptr;
    std::uint64_t size_ = 0;
    StoreHeader header_{};
};

inline const json& argument(
    const json& input, std::size_t index, const std::string& name) {
    if (input.is_array()) return input.at(index);
    if (input.is_object()) return input.at(name);
    throw std::runtime_error("case input must be a JSON array or object");
}

inline bool judge_equal(const json& expected, const json& output) {
    if (expected.is_boolean() && output.is_number()) {
        return output == json(expected.get<bool>() ? 1 : 0);
    }
    if (output.is_boolean() && expected.is_number()) {
        return expected == json(output.get<bool>() ? 1 : 0);
    }
    if (expected.is_number() && output.is_number()) {
        return expected == output;
    }
    if (expected.is_array() && output.is_array()) {
        if (expected.size() != output.size()) return false;
        for (std::size_t index = 0; index < expected.size(); ++index) {
            if (!judge_equal(expected[index], output[index])) return false;
        }
        return true;
    }
    if (expected.is_object() && output.is_object()) {
        if (expected.size() != output.size()) return false;
        for (json::const_iterator item = expected.begin(); item != expected.end(); ++item) {
            const json::const_iterator found = output.find(item.key());
            if (found == output.end() || !judge_equal(item.value(), *found)) return false;
        }
        return true;
    }
    return expected == output;
}

inline bool same_digest_value(const json& expected, const json& output) {
    if (expected.is_number_integer() && output.is_number_integer()) {
        return expected.dump() == output.dump();
    }
    if (expected.is_number_float() && output.is_number_float()) {
        const double left = expected.get<double>();
        const double right = output.get<double>();
        return left == right && std::signbit(left) == std::signbit(right);
    }
    if (expected.type() != output.type()) return false;
    if (expected.is_array()) {
        if (expected.size() != output.size()) return false;
        for (std::size_t index = 0; index < expected.size(); ++index) {
            if (!same_digest_value(expected[index], output[index])) return false;
        }
        return true;
    }
    if (expected.is_object()) {
        if (expected.size() != output.size()) return false;
        for (json::const_iterator item = expected.begin(); item != expected.end(); ++item) {
            const json::const_iterator found = output.find(item.key());
            if (found == output.end() || !same_digest_value(item.value(), *found)) {
                return false;
            }
        }
        return true;
    }
    return expected == output;
}

inline void validate_finite_output(const json& value) {
    if (value.is_number_float() && !std::isfinite(value.get<double>())) {
        throw std::runtime_error("non-finite floating-point output is not supported");
    }
    if (value.is_array()) {
        for (const json& item : value) validate_finite_output(item);
    } else if (value.is_object()) {
        for (json::const_iterator item = value.begin(); item != value.end(); ++item) {
            validate_finite_output(item.value());
        }
    }
}

inline std::map<std::string, std::string> parse_args(int argc, char** argv) {
    std::map<std::string, std::string> result;
    for (int index = 1; index < argc; index += 2) {
        if (index + 1 >= argc || std::string(argv[index]).rfind("--", 0) != 0) {
            throw std::runtime_error("arguments must be --name value pairs");
        }
        result[argv[index]] = argv[index + 1];
    }
    return result;
}

inline std::string required(
    const std::map<std::string, std::string>& args, const std::string& name) {
    const auto found = args.find(name);
    if (found == args.end() || found->second.empty()) {
        throw std::runtime_error("missing argument: " + name);
    }
    return found->second;
}

inline std::uint64_t parse_u64(
    const std::map<std::string, std::string>& args, const std::string& name) {
    const std::string raw = required(args, name);
    std::size_t consumed = 0;
    const unsigned long long value = std::stoull(raw, &consumed, 10);
    if (consumed != raw.size()) throw std::runtime_error("invalid integer: " + name);
    return static_cast<std::uint64_t>(value);
}

inline std::uint64_t current_rss_bytes() {
    PROCESS_MEMORY_COUNTERS counters;
    std::memset(&counters, 0, sizeof(counters));
    counters.cb = sizeof(counters);
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters))) {
        return 0;
    }
    return static_cast<std::uint64_t>(counters.WorkingSetSize);
}

inline void write_json_atomically(
    const std::filesystem::path& destination, const json& payload) {
    std::filesystem::create_directories(destination.parent_path());
    std::filesystem::path temporary = destination;
    temporary += L".writing";
    {
        std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
        if (!stream) throw std::runtime_error("cannot create result file");
        stream << payload.dump();
        if (!stream) throw std::runtime_error("cannot write result file");
    }
    if (!MoveFileExW(
            temporary.c_str(), destination.c_str(),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        std::error_code ignored;
        std::filesystem::remove(temporary, ignored);
        throw std::runtime_error("cannot publish result file");
    }
}

template <typename Invoke>
int worker_main(int argc, char** argv, Invoke invoke) {
    const auto wall_started = std::chrono::steady_clock::now();
    std::map<std::string, std::string> args;
    int worker_id = -1;
    std::filesystem::path result_dir;
    try {
        args = parse_args(argc, argv);
        worker_id = static_cast<int>(parse_u64(args, "--worker-id"));
        result_dir = std::filesystem::u8path(required(args, "--result-dir"));
        const std::uint64_t start = parse_u64(args, "--start");
        const std::uint64_t stop = parse_u64(args, "--stop");
        MappedCaseStore store(required(args, "--store"));
        if (stop < start || stop > store.size()) {
            throw std::runtime_error("invalid worker case range");
        }

        // Native summaries do not return stdout. Suppress both iostream and
        // stdio output from the student method once per worker process.
        std::freopen("NUL", "w", stdout);

        std::uint64_t correct = 0;
        std::uint64_t wrong = 0;
        std::uint64_t errors = 0;
        double decode_seconds = 0.0;
        double compute_seconds = 0.0;
        Digest128 digest;
        json fallback_results = json::array();
        std::string first_error;

        for (std::uint64_t index = start; index < stop; ++index) {
            const auto decode_started = std::chrono::steady_clock::now();
            CaseRecord record = store.read(index);
            decode_seconds += std::chrono::duration<double>(
                std::chrono::steady_clock::now() - decode_started).count();

            const auto compute_started = std::chrono::steady_clock::now();
            json output = nullptr;
            json error = nullptr;
            bool is_wrong = false;
            try {
                output = invoke(record.value.at("input"));
                validate_finite_output(output);
                if (record.value.contains("expected")) {
                    is_wrong = !judge_equal(record.value.at("expected"), output);
                }
            } catch (const std::exception& exception) {
                error = std::string("RuntimeError: ") + exception.what();
            } catch (...) {
                error = "RuntimeError: unknown C++ exception";
            }
            compute_seconds += std::chrono::duration<double>(
                std::chrono::steady_clock::now() - compute_started).count();

            if (!error.is_null()) {
                ++errors;
                if (first_error.empty()) first_error = error.get<std::string>();
            } else if (is_wrong) {
                ++wrong;
            } else {
                ++correct;
            }

            const bool can_use_expected =
                record.expected_digest.has_value() && error.is_null() && !is_wrong &&
                same_digest_value(record.value.at("expected"), output);
            if (can_use_expected) {
                digest.xor_with(*record.expected_digest);
            } else {
                fallback_results.push_back(json{
                    {"index", index},
                    {"cid", record.value.value("cid", json(index))},
                    {"output", output},
                    {"error", error}});
            }
        }

        const double wall_seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - wall_started).count();
        const json summary{
            {"worker_id", worker_id},
            {"start", start},
            {"stop", stop},
            {"correct", correct},
            {"wrong", wrong},
            {"errors", errors},
            {"first_error", first_error.empty() ? json(nullptr) : json(first_error)},
            {"digest", digest.hex()},
            {"fallback_results", std::move(fallback_results)},
            {"wall_seconds", wall_seconds},
            {"compute_seconds", compute_seconds},
            {"decode_seconds", decode_seconds},
            {"rss_bytes", current_rss_bytes()}};
        const std::filesystem::path destination =
            result_dir / ("worker_" + std::to_string(worker_id) + ".json");
        write_json_atomically(destination, summary);
        return 0;
    } catch (const std::exception& exception) {
        try {
            if (!result_dir.empty() && worker_id >= 0) {
                std::filesystem::create_directories(result_dir);
                std::ofstream stream(
                    result_dir / ("worker_" + std::to_string(worker_id) + ".error.txt"),
                    std::ios::binary | std::ios::trunc);
                stream << exception.what();
            }
        } catch (...) {
        }
        std::fprintf(stderr, "oj_cpp_worker: %s\n", exception.what());
        return 1;
    }
}

}  // namespace oj_cpp_runtime
