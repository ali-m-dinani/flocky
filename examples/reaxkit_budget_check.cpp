#include "../run_budget.h"
#include <cassert>
#include <thread>

int main() {
    RunBudget budget;
    budget.begin();
    assert(!budget.stop());
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    assert(budget.stop());
    budget.publish(true);
}
