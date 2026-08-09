#include <windows.h>

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::wstring utf8_to_wide(const std::string& value) {
    if (value.empty()) return std::wstring();
    int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
                                   static_cast<int>(value.size()), NULL, 0);
    if (size <= 0) throw std::runtime_error("invalid UTF-8 argument");
    std::wstring result(static_cast<std::size_t>(size), L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
                        static_cast<int>(value.size()), &result[0], size);
    return result;
}

std::wstring quote(const std::wstring& value) {
    std::wstring escaped = L"\"";
    unsigned backslashes = 0;
    for (std::wstring::const_iterator it = value.begin(); it != value.end(); ++it) {
        if (*it == L'\\') {
            ++backslashes;
        } else if (*it == L'\"') {
            escaped.append(backslashes * 2 + 1, L'\\');
            escaped.push_back(L'\"');
            backslashes = 0;
        } else {
            escaped.append(backslashes, L'\\');
            backslashes = 0;
            escaped.push_back(*it);
        }
    }
    escaped.append(backslashes * 2, L'\\');
    escaped.push_back(L'\"');
    return escaped;
}

long long parse_integer(const std::map<std::string, std::string>& args,
                        const std::string& name, long long default_value = -1) {
    std::map<std::string, std::string>::const_iterator found = args.find(name);
    if (found == args.end()) return default_value;
    char* end = NULL;
    const long long value = std::strtoll(found->second.c_str(), &end, 10);
    if (!end || *end != '\0') throw std::runtime_error("invalid integer: " + name);
    return value;
}

std::map<std::string, std::string> parse_args(int argc, char** argv) {
    std::map<std::string, std::string> result;
    for (int index = 1; index < argc; index += 2) {
        if (index + 1 >= argc || std::string(argv[index]).find("--") != 0) {
            throw std::runtime_error("arguments must be --name value pairs");
        }
        result[argv[index]] = argv[index + 1];
    }
    return result;
}

std::string required(const std::map<std::string, std::string>& args,
                     const std::string& name) {
    std::map<std::string, std::string>::const_iterator found = args.find(name);
    if (found == args.end() || found->second.empty()) {
        throw std::runtime_error("missing argument: " + name);
    }
    return found->second;
}

void close_process(PROCESS_INFORMATION& process) {
    if (process.hThread) CloseHandle(process.hThread);
    if (process.hProcess) CloseHandle(process.hProcess);
    process.hThread = NULL;
    process.hProcess = NULL;
}

}  // namespace

int main(int argc, char** argv) {
    HANDLE job = NULL;
    std::vector<PROCESS_INFORMATION> processes;
    try {
        const std::map<std::string, std::string> args = parse_args(argc, argv);
        const std::string python = required(args, "--python");
        const std::string worker_script = required(args, "--worker-script");
        const std::string store = required(args, "--store");
        const std::string solution = required(args, "--solution");
        const std::string method = required(args, "--method");
        const std::string result_dir = required(args, "--result-dir");
        const std::string workspace = required(args, "--workspace");
        const long long case_count = parse_integer(args, "--case-count");
        const long long requested_workers = parse_integer(args, "--workers");
        const long long memory_mb = parse_integer(args, "--memory-mb", 512);
        const long long timeout_ms = parse_integer(args, "--timeout-ms", 0);
        const long long standard_mode = parse_integer(args, "--standard-mode", 0);
        if (case_count < 0 || requested_workers < 1 || requested_workers > 16 ||
            memory_mb < 64) {
            throw std::runtime_error("invalid case-count/workers/memory limit");
        }
        const int workers = static_cast<int>(
            std::min<long long>(requested_workers, std::max<long long>(1, case_count)));

        job = CreateJobObjectW(NULL, NULL);
        if (!job) throw std::runtime_error("CreateJobObject failed");
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits;
        ZeroMemory(&limits, sizeof(limits));
        limits.BasicLimitInformation.LimitFlags =
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE |
            JOB_OBJECT_LIMIT_ACTIVE_PROCESS |
            JOB_OBJECT_LIMIT_PROCESS_MEMORY;
        limits.BasicLimitInformation.ActiveProcessLimit = static_cast<DWORD>(workers);
        limits.ProcessMemoryLimit = static_cast<SIZE_T>(memory_mb) * 1024u * 1024u;
        if (!SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                     &limits, sizeof(limits))) {
            throw std::runtime_error("SetInformationJobObject failed");
        }

        const long long base = case_count / workers;
        const long long extra = case_count % workers;
        long long start = 0;
        for (int worker_id = 0; worker_id < workers; ++worker_id) {
            const long long length = base + (worker_id < extra ? 1 : 0);
            const long long stop = start + length;
            std::wostringstream command;
            command << quote(utf8_to_wide(python)) << L" "
                    << quote(utf8_to_wide(worker_script))
                    << L" --worker-id " << worker_id
                    << L" --store " << quote(utf8_to_wide(store))
                    << L" --solution " << quote(utf8_to_wide(solution))
                    << L" --method " << quote(utf8_to_wide(method))
                    << L" --start " << start
                    << L" --stop " << stop
                    << L" --result-dir " << quote(utf8_to_wide(result_dir))
                    << L" --standard-mode " << standard_mode;
            std::wstring mutable_command = command.str();
            std::vector<wchar_t> buffer(mutable_command.begin(), mutable_command.end());
            buffer.push_back(L'\0');

            STARTUPINFOW startup;
            PROCESS_INFORMATION process;
            ZeroMemory(&startup, sizeof(startup));
            ZeroMemory(&process, sizeof(process));
            startup.cb = sizeof(startup);
            startup.dwFlags = STARTF_USESTDHANDLES;
            startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
            startup.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
            startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
            const std::wstring wide_workspace = utf8_to_wide(workspace);
            if (!CreateProcessW(NULL, &buffer[0], NULL, NULL, TRUE,
                                CREATE_SUSPENDED | CREATE_NO_WINDOW, NULL,
                                wide_workspace.c_str(), &startup, &process)) {
                throw std::runtime_error("CreateProcessW failed");
            }
            if (!AssignProcessToJobObject(job, process.hProcess)) {
                TerminateProcess(process.hProcess, 1);
                close_process(process);
                throw std::runtime_error("AssignProcessToJobObject failed");
            }
            ResumeThread(process.hThread);
            processes.push_back(process);
            start = stop;
        }

        std::vector<HANDLE> handles;
        for (std::size_t index = 0; index < processes.size(); ++index) {
            handles.push_back(processes[index].hProcess);
        }
        const DWORD wait_timeout = timeout_ms > 0 ? static_cast<DWORD>(timeout_ms) : INFINITE;
        const DWORD wait_result = WaitForMultipleObjects(
            static_cast<DWORD>(handles.size()), &handles[0], TRUE, wait_timeout);
        if (wait_result == WAIT_TIMEOUT) {
            TerminateJobObject(job, 124);
            throw std::runtime_error("native worker batch timed out");
        }
        if (wait_result == WAIT_FAILED) {
            throw std::runtime_error("WaitForMultipleObjects failed");
        }

        int exit_code = 0;
        for (std::size_t index = 0; index < processes.size(); ++index) {
            DWORD child_code = 1;
            GetExitCodeProcess(processes[index].hProcess, &child_code);
            if (child_code != 0) {
                std::cerr << "worker " << index << " exited with " << child_code << "\n";
                exit_code = 2;
            }
            close_process(processes[index]);
        }
        CloseHandle(job);
        std::cout << "workers=" << workers << " cases=" << case_count
                  << " sandbox=job_object\n";
        return exit_code;
    } catch (const std::exception& error) {
        if (job) TerminateJobObject(job, 1);
        for (std::size_t index = 0; index < processes.size(); ++index) {
            close_process(processes[index]);
        }
        if (job) CloseHandle(job);
        std::cerr << "oj_native_manager: " << error.what() << "\n";
        return 1;
    }
}
