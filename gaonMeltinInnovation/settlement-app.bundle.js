(() => {
    const root = document.getElementById("settlement-app");
    if (!root) return;

    const UNIT_CONFIG = {
        M: { maxDigits: 99, label: "M", decimals: 3 },
        K: { maxDigits: 10, label: "K", decimals: 0 },
    };

    const SETTLEMENT_COOKIE_KEY = "gaon_settlement_state";
    const SETTLEMENT_COOKIE_MAX_AGE = 60 * 60 * 24 * 14; // 14 days

    const state = {
        teamName: "",
        currentCash: 15,
        turn: 1,
        history: [],
        unit: "M",
        inputs: {
            salary: 0,
            rentIn: 0,
            tradeIn: 0,
            etcIn: 0,
            invest: 0,
            rentOut: 0,
            tradeOut: 0,
            donation: 0,
            fine: 0,
        },
    };

    let hasLoaded = false;

    const getCookieValue = (name) => {
        const cookies = `; ${document.cookie}`;
        const parts = cookies.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return null;
    };

    const loadSettlementState = () => {
        const storedValue = getCookieValue(SETTLEMENT_COOKIE_KEY);
        if (!storedValue) return null;

        try {
            return JSON.parse(decodeURIComponent(storedValue));
        } catch (error) {
            return null;
        }
    };

    const saveSettlementState = () => {
        const encoded = encodeURIComponent(
            JSON.stringify({
                teamName: state.teamName,
                currentCash: state.currentCash,
                turn: state.turn,
                history: state.history,
                inputs: state.inputs,
                unit: state.unit,
            })
        );
        document.cookie = `${SETTLEMENT_COOKIE_KEY}=${encoded}; path=/; max-age=${SETTLEMENT_COOKIE_MAX_AGE}; samesite=lax`;
    };

    const sanitizeInputValue = (value, activeUnit) => {
        if (value === "") return value;
        if (value.includes("-")) return null;
        const normalizedValue = activeUnit === "M" ? value.replace(",", ".") : value;
        if (activeUnit === "K" && normalizedValue.includes(".")) return null;
        if (activeUnit === "M" && !/^\d*(\.\d{0,3})?$/.test(normalizedValue)) return null;
        if (activeUnit === "K" && !/^\d*$/.test(normalizedValue)) return null;

        const digits = normalizedValue.replace(/\D/g, "");
        if (digits.length > UNIT_CONFIG[activeUnit].maxDigits) {
            return null;
        }

        const numericValue = parseFloat(normalizedValue);
        if (!Number.isNaN(numericValue) && numericValue < 0) {
            return null;
        }

        return normalizedValue;
    };

    const roundTo = (value, decimals) => {
        const factor = 10 ** decimals;
        return Math.round(value * factor) / factor;
    };

    const toInternalValue = (value, activeUnit) => {
        const numericValue = parseFloat(value);
        if (Number.isNaN(numericValue)) return 0;

        const inM = activeUnit === "M" ? numericValue : numericValue / 1000;
        return roundTo(inM, activeUnit === "M" ? 1 : 3);
    };

    const formatAmount = (valueInM) => {
        const multiplier = state.unit === "M" ? 1 : 1000;
        const rawValue = valueInM * multiplier;
        const rounded =
            state.unit === "M" ? roundTo(rawValue, 3) : Math.round(rawValue);
        const hasDecimal = rounded % 1 !== 0;
        return rounded.toLocaleString(undefined, {
            minimumFractionDigits: hasDecimal ? 1 : 0,
            maximumFractionDigits: state.unit === "M" ? 3 : 0,
        });
    };

    const formatInputNumber = (value, decimals) => {
        if (Number.isNaN(value)) return "";
        const fixed = value.toFixed(decimals);
        return fixed.replace(/\.?0+$/, "");
    };

    const getDisplayValue = (valueInM) => {
        if (valueInM === 0) return "";
        const displayValue = state.unit === "M" ? valueInM : valueInM * 1000;
        if (state.unit === "M") {
            return formatInputNumber(displayValue, UNIT_CONFIG.M.decimals);
        }
        return Math.round(displayValue).toString();
    };

    const normalizeInputValue = (value, activeUnit) => {
        if (value === "") return value;
        const normalizedValue = activeUnit === "M" ? value.replace(",", ".") : value;
        const numericValue = parseFloat(normalizedValue);
        if (Number.isNaN(numericValue)) return "";

        if (activeUnit === "M") {
            return Math.max(0, roundTo(numericValue, 1)).toString();
        }
        return Math.max(0, Math.round(numericValue)).toString();
    };

    const setInputs = (patch) => {
        state.inputs = { ...state.inputs, ...patch };
    };

    const handleInputChange = (field, value) => {
        const rawValue = typeof value === "number" ? value.toString() : value;
        const sanitized = sanitizeInputValue(rawValue, state.unit);
        if (sanitized === null) return;

        setInputs({
            [field]: sanitized === "" ? 0 : Math.max(0, toInternalValue(sanitized, state.unit)),
        });
    };

    const finishTurn = () => {
        const totalIncome =
            state.inputs.salary +
            state.inputs.rentIn +
            state.inputs.tradeIn +
            state.inputs.etcIn;
        const totalExpense =
            state.inputs.invest +
            state.inputs.rentOut +
            state.inputs.tradeOut +
            state.inputs.donation +
            state.inputs.fine;
        const turnProfit = totalIncome - totalExpense;

        if (totalIncome === 0 && totalExpense === 0) {
            if (!window.confirm("수입/지출 내역이 없습니다. 이대로 턴을 넘기시겠습니까? ")) {
                return;
            }
        }

        const newBalance = state.currentCash + turnProfit;
        const turnData = {
            id: Date.now(),
            turn: state.turn,
            income: totalIncome,
            expense: totalExpense,
            profit: turnProfit,
            balance: newBalance,
            details: { ...state.inputs },
        };

        state.history = [turnData, ...state.history];
        state.currentCash = newBalance;
        state.turn += 1;
        setInputs({
            salary: 0,
            rentIn: 0,
            tradeIn: 0,
            etcIn: 0,
            invest: 0,
            rentOut: 0,
            tradeOut: 0,
            donation: 0,
            fine: 0,
        });
    };

    const resetGame = () => {
        if (window.confirm("모든 기록을 지우고 게임을 처음부터 시작할까요?")) {
            state.turn = 1;
            state.currentCash = 15;
            state.history = [];
            setInputs({
                salary: 0,
                rentIn: 0,
                tradeIn: 0,
                etcIn: 0,
                invest: 0,
                rentOut: 0,
                tradeOut: 0,
                donation: 0,
                fine: 0,
            });
        }
    };

    const undoLastTurn = () => {
        if (state.history.length === 0) return;
        if (!window.confirm("마지막 턴 기록을 삭제하고 되돌리겠습니까?")) return;

        const [lastTurn, ...rest] = state.history;
        state.history = rest;
        state.currentCash = lastTurn.balance - lastTurn.profit;
        state.turn = lastTurn.turn;
    };

    const escapeHtml = (value) => {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    const render = (restoreFocus) => {
        const totalIncome =
            state.inputs.salary +
            state.inputs.rentIn +
            state.inputs.tradeIn +
            state.inputs.etcIn;
        const totalExpense =
            state.inputs.invest +
            state.inputs.rentOut +
            state.inputs.tradeOut +
            state.inputs.donation +
            state.inputs.fine;
        const turnProfit = totalIncome - totalExpense;

        const inputField = (label, field, color) => {
            const colorClasses =
                color === "red"
                    ? "border-red-200 focus:ring-red-500 text-red-700"
                    : "border-blue-200 focus:ring-blue-500 text-blue-700";
            return `
                <div class="flex flex-col mb-2">
                    <label class="text-xs text-gray-500 font-bold mb-1">${label}</label>
                    <div class="flex items-center">
                        <input
                            type="text"
                            inputmode="${state.unit === "K" ? "numeric" : "decimal"}"
                            pattern="${state.unit === "K" ? "[0-9]*" : "[0-9]*[.,]?[0-9]*"}"
                            data-field="${field}"
                            value="${getDisplayValue(state.inputs[field])}"
                            placeholder="0"
                            class="w-full p-2 border rounded-lg focus:outline-none focus:ring-2 text-right font-mono text-lg bg-white ${colorClasses}"
                        />
                        <span class="ml-2 text-gray-400 text-sm">${UNIT_CONFIG[state.unit].label}</span>
                    </div>
                </div>
            `;
        };

        const historyMarkup =
            state.history.length === 0
                ? `
                    <div class="text-center py-8 text-gray-400 bg-white rounded-xl border border-dashed border-gray-300">
                        아직 기록된 내용이 없습니다.
                        <br />
                        게임을 시작해보세요!
                    </div>
                `
                : state.history
                      .map((record) => {
                          const profitClass =
                              record.profit >= 0 ? "text-blue-600" : "text-red-500";
                          return `
                              <div
                                  class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex justify-between items-center"
                              >
                                  <div>
                                      <div class="flex items-center gap-2 mb-1">
                                          <span class="bg-gray-100 text-gray-600 text-xs font-bold px-2 py-0.5 rounded">
                                              TURN ${record.turn}
                                          </span>
                                          <span class="text-sm font-bold ${profitClass}">
                                              ${record.profit > 0 ? "+" : ""}${formatAmount(record.profit)} ${state.unit}
                                          </span>
                                      </div>
                                      <div class="text-xs text-gray-400">
                                          수입 ${formatAmount(record.income)} / 지출 ${formatAmount(record.expense)}
                                      </div>
                                  </div>
                                  <div class="text-right">
                                      <div class="text-xs text-gray-400">잔액</div>
                                      <div class="font-bold text-gray-800 text-lg">
                                          ${formatAmount(record.balance)} ${state.unit}
                                      </div>
                                  </div>
                              </div>
                          `;
                      })
                      .join("");

        root.innerHTML = `
            <div class="min-h-screen bg-gray-100 p-4 w-full max-w-none mx-auto font-sans rounded-2xl border border-gray-100">
                <header class="bg-white rounded-2xl p-6 shadow-sm mb-4 border border-gray-200">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <input
                                type="text"
                                placeholder="조 이름 입력"
                                class="text-lg font-bold text-gray-800 placeholder-gray-300 focus:outline-none bg-transparent w-32"
                                value="${escapeHtml(state.teamName)}"
                                data-field="teamName"
                            />
                            <p class="text-xs text-gray-400">모노폴리 손익계산기</p>
                        </div>
                        <button
                            data-action="reset"
                            class="text-gray-400 hover:text-red-500"
                            aria-label="정산 초기화"
                        >
                            <i class="fa-solid fa-rotate-left"></i>
                        </button>
                    </div>

                    <div class="text-center">
                        <p class="text-sm text-gray-500 mb-1">현재 보유 자산 </p>
                        <div class="text-5xl font-black text-blue-600 tracking-tight flex justify-center items-baseline">
                            ${formatAmount(state.currentCash)}
                            <span class="text-2xl ml-1 text-blue-400">${state.unit}</span>
                        </div>
                    </div>
                    <div class="mt-3 flex justify-center">
                        <div class="inline-flex rounded-full bg-gray-100 p-1">
                            ${["M", "K"]
                                .map((value) => {
                                    const isActive = state.unit === value;
                                    return `
                                        <button
                                            data-action="set-unit"
                                            data-unit="${value}"
                                            class="px-3 py-1 text-xs font-bold rounded-full transition ${
                                                isActive
                                                    ? "bg-blue-600 text-white shadow"
                                                    : "text-gray-500 hover:text-gray-700"
                                            }"
                                        >
                                            ${value} 단위로 보기
                                        </button>
                                    `;
                                })
                                .join("")}
                        </div>
                    </div>
                </header>

                <div class="bg-white rounded-2xl shadow-lg border border-blue-100 overflow-hidden mb-6">
                    <div class="bg-blue-600 text-white p-3 flex justify-between items-center">
                        <h2 class="font-bold text-lg flex items-center">
                            <span class="bg-white text-blue-600 text-xs px-2 py-1 rounded-full mr-2 font-black">
                                TURN ${state.turn}
                            </span>
                            이번 턴 기록
                        </h2>
                        <span class="text-xs opacity-80">단위: ${state.unit} (1M=1000K)</span>
                    </div>

                    <div class="p-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-blue-50 p-3 rounded-xl">
                                <h3 class="text-blue-700 font-bold mb-3 flex items-center text-sm border-b border-blue-200 pb-1">
                                    <i class="fa-solid fa-arrow-trend-up mr-1"></i> 수입
                                </h3>

                                <div class="mb-3">
                                    <div class="flex justify-between items-end mb-1">
                                        <label class="text-xs font-bold text-gray-500">월급</label>
                                        <button
                                            data-action="set-input"
                                            data-field="salary"
                                            data-value="2"
                                            class="text-[10px] bg-blue-200 text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-300"
                                        >
                                            +2M
                                        </button>
                                    </div>
                                    <input
                                        type="text"
                                        inputmode="${state.unit === "K" ? "numeric" : "decimal"}"
                                        pattern="${state.unit === "K" ? "[0-9]*" : "[0-9]*[.,]?[0-9]*"}"
                                        value="${getDisplayValue(state.inputs.salary)}"
                                        data-field="salary"
                                        class="w-full p-2 border border-blue-200 rounded-lg text-right font-mono text-blue-700"
                                        placeholder="0"
                                    />
                                </div>

                                ${inputField("통행료 수입", "rentIn", "blue")}
                                ${inputField("사업 매각", "tradeIn", "blue")}
                                ${inputField("복불복 카드", "etcIn", "blue")}
                            </div>

                            <div class="bg-red-50 p-3 rounded-xl">
                                <h3 class="text-red-700 font-bold mb-3 flex items-center text-sm border-b border-red-200 pb-1">
                                    <i class="fa-solid fa-arrow-trend-down mr-1"></i> 지출
                                </h3>

                                ${inputField("사업 투자 비용", "invest", "red")}
                                ${inputField("통행료 지출", "rentOut", "red")}

                                <div class="mb-2">
                                    <div class="flex justify-between items-end mb-1">
                                        <label class="text-xs font-bold text-gray-500">사회공헌</label>
                                        <button
                                            data-action="set-input"
                                            data-field="donation"
                                            data-value="1"
                                            class="text-[10px] bg-red-200 text-red-700 px-1.5 py-0.5 rounded hover:bg-red-300"
                                        >
                                            -1M
                                        </button>
                                    </div>
                                    <input
                                        type="text"
                                        inputmode="${state.unit === "K" ? "numeric" : "decimal"}"
                                        pattern="${state.unit === "K" ? "[0-9]*" : "[0-9]*[.,]?[0-9]*"}"
                                        value="${getDisplayValue(state.inputs.donation)}"
                                        data-field="donation"
                                        class="w-full p-2 border border-red-200 rounded-lg text-right font-mono text-red-700"
                                        placeholder="0"
                                    />
                                </div>

                                ${inputField("손실 발생", "fine", "red")}
                                ${inputField("복불복 카드", "tradeOut", "red")}
                            </div>
                        </div>

                        <div class="mt-4 p-3 bg-gray-800 rounded-xl text-white flex justify-between items-center shadow-lg">
                            <div class="text-sm text-gray-400">
                                <span class="text-blue-400">+${formatAmount(totalIncome)}</span> /
                                <span class="text-red-400">-${formatAmount(totalExpense)}</span>
                            </div>
                            <div class="text-right">
                                <span class="text-xs text-gray-400 block">이번 턴 손익</span>
                                <span class="text-xl font-bold ${
                                    turnProfit >= 0 ? "text-green-400" : "text-red-400"
                                }">
                                    ${turnProfit > 0 ? "+" : ""}${formatAmount(turnProfit)} ${state.unit}
                                </span>
                            </div>
                        </div>

                        <button
                            data-action="finish"
                            class="w-full mt-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl shadow-md transition flex items-center justify-center"
                        >
                            <i class="fa-solid fa-floppy-disk mr-2"></i> 턴 종료 및 저장
                        </button>
                    </div>
                </div>

                <div class="space-y-3">
                    <h3 class="font-bold text-gray-500 text-sm flex items-center px-2">
                        <i class="fa-regular fa-clock mr-2"></i> 지난 턴 기록
                        ${
                            state.history.length > 0
                                ? `
                                    <button
                                        data-action="undo"
                                        class="ml-auto text-xs text-red-400 underline"
                                    >
                                        마지막 턴 취소
                                    </button>
                                `
                                : ""
                        }
                    </h3>

                    ${historyMarkup}
                </div>

                <div class="mt-8 text-center pb-8">
                    <p class="text-xs text-gray-400">
                        * 실제 카드 결제기에는 턴이 끝난 후
                        <br />
                        최종 계산된 금액만 입력하면 됩니다.
                    </p>
                </div>
            </div>
        `;

        if (restoreFocus?.field) {
            const nextInput = root.querySelector(`[data-field="${restoreFocus.field}"]`);
            if (nextInput) {
                nextInput.focus();
                if (typeof restoreFocus.start === "number") {
                    nextInput.setSelectionRange(restoreFocus.start, restoreFocus.end);
                }
            }
        }
    };

    const updateAndRender = (updater) => {
        const activeElement = document.activeElement;
        const restoreFocus =
            activeElement && root.contains(activeElement) && activeElement.dataset?.field
                ? {
                      field: activeElement.dataset.field,
                      start: activeElement.selectionStart,
                      end: activeElement.selectionEnd,
                  }
                : null;

        updater();
        if (hasLoaded) {
            saveSettlementState();
        }
        render(restoreFocus);
    };

    root.addEventListener("input", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;

        const field = target.dataset.field;
        if (!field) return;

        if (field === "teamName") {
            updateAndRender(() => {
                state.teamName = target.value;
            });
            return;
        }

        updateAndRender(() => {
            handleInputChange(field, target.value);
        });
    });

    root.addEventListener(
        "blur",
        (event) => {
            const target = event.target;
            if (!(target instanceof HTMLInputElement)) return;
            const field = target.dataset.field;
            if (!field || field === "teamName") return;

            const normalized = normalizeInputValue(target.value, state.unit);
            if (normalized === "" && target.value === "") return;
            if (normalized === "") return;

            updateAndRender(() => {
                handleInputChange(field, normalized);
            });
        },
        true
    );

    root.addEventListener("click", (event) => {
        const target = event.target instanceof Element ? event.target.closest("[data-action]") : null;
        if (!target) return;

        const action = target.getAttribute("data-action");
        if (!action) return;

        if (action === "reset") {
            updateAndRender(() => {
                resetGame();
            });
            return;
        }

        if (action === "finish") {
            updateAndRender(() => {
                finishTurn();
            });
            return;
        }

        if (action === "undo") {
            updateAndRender(() => {
                undoLastTurn();
            });
            return;
        }

        if (action === "set-unit") {
            const unit = target.getAttribute("data-unit");
            if (!unit || (unit !== "M" && unit !== "K")) return;
            updateAndRender(() => {
                state.unit = unit;
            });
            return;
        }

        if (action === "set-input") {
            const field = target.getAttribute("data-field");
            const value = Number(target.getAttribute("data-value"));
            if (!field || Number.isNaN(value)) return;
            updateAndRender(() => {
                setInputs({ [field]: value });
            });
        }
    });

    const storedState = loadSettlementState();
    if (storedState) {
        state.teamName = storedState.teamName ?? "";
        state.currentCash = storedState.currentCash ?? 15;
        state.turn = storedState.turn ?? 1;
        state.history = Array.isArray(storedState.history) ? storedState.history : [];
        state.unit = storedState.unit ?? "M";
        state.inputs = {
            salary: storedState.inputs?.salary ?? 0,
            rentIn: storedState.inputs?.rentIn ?? 0,
            tradeIn: storedState.inputs?.tradeIn ?? 0,
            etcIn: storedState.inputs?.etcIn ?? 0,
            invest: storedState.inputs?.invest ?? 0,
            rentOut: storedState.inputs?.rentOut ?? 0,
            tradeOut: storedState.inputs?.tradeOut ?? 0,
            donation: storedState.inputs?.donation ?? 0,
            fine: storedState.inputs?.fine ?? 0,
        };
    }

    hasLoaded = true;
    render();
})();
