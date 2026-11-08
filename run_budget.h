#pragma once
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

class RunBudget {
    using Clock = std::chrono::steady_clock;
    Clock::time_point created = Clock::now();
    Clock::time_point started = created;
    bool active = false;
    bool expired = false;
    double seconds = 0;
    std::string path;
public:
    RunBudget() {
        const char* value = std::getenv("REAXKIT_OPTIMIZATION_TIME_LIMIT_SECONDS");
        if (value) {
            seconds = std::stod(value);
            if (!std::isfinite(seconds) || seconds <= 0) throw std::runtime_error("Invalid time budget");
        }
        const char* target = std::getenv("REAXKIT_TIMING_FILE");
        path = target ? target : "optimization-timing.json";
    }
    void begin() {
        if (!active) { started = Clock::now(); active = true; }
        publish(false);
    }
    bool stop() {
        if (!active) return false;
        if (seconds > 0 && std::chrono::duration<double>(Clock::now()-started).count() >= seconds) expired = true;
        const char* marker = std::getenv("REAXKIT_STOP_FILE");
        if (marker && std::ifstream(marker).good()) expired = true;
        publish(false);
        return expired;
    }
    void publish(bool done) {
        std::ofstream stream(path + ".tmp");
        stream << std::setprecision(17)
               << "{\"schema_version\":1,\"updated_at_epoch\":"
               << std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count()
               << ",\"clock_scope\":\"optimizer_entrypoint\",\"initialization_seconds\":"
               << std::chrono::duration<double>(started-created).count()
               << ",\"optimization_elapsed_seconds\":" << std::chrono::duration<double>(Clock::now()-started).count()
               << ",\"graceful\":" << (done ? "true" : "false")
               << ",\"termination_reason\":\"" << (expired ? "time_limit" : "optimizer_criteria")
               << "\",\"state\":\"" << (done ? "completed" : "running") << "\"}\n";
        stream.close();
        if (std::rename((path + ".tmp").c_str(), path.c_str()) != 0) throw std::runtime_error("Cannot publish timing");
    }
};

inline RunBudget& run_budget() { static RunBudget budget; return budget; }
