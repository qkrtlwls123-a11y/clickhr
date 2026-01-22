(() => {
  // ../../tmp/settlement-app.jsx
  var { useState, useEffect, useRef } = React;
  var SETTLEMENT_COOKIE_KEY = "gaon_settlement_state";
  var SETTLEMENT_COOKIE_MAX_AGE = 60 * 60 * 24 * 14;
  var getCookieValue = (name) => {
    const cookies = `; ${document.cookie}`;
    const parts = cookies.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
    return null;
  };
  var loadSettlementState = () => {
    const storedValue = getCookieValue(SETTLEMENT_COOKIE_KEY);
    if (!storedValue)
      return null;
    try {
      return JSON.parse(decodeURIComponent(storedValue));
    } catch (error) {
      return null;
    }
  };
  var saveSettlementState = (state) => {
    const encoded = encodeURIComponent(JSON.stringify(state));
    document.cookie = `${SETTLEMENT_COOKIE_KEY}=${encoded}; path=/; max-age=${SETTLEMENT_COOKIE_MAX_AGE}; samesite=lax`;
  };
  var InputField = ({
    label,
    field,
    color = "blue",
    unit,
    inputs,
    onChange,
    unitConfig,
    colorClasses
  }) => /* @__PURE__ */ React.createElement("div", {
    className: "flex flex-col mb-2"
  }, /* @__PURE__ */ React.createElement("label", {
    className: "text-xs text-gray-500 font-bold mb-1"
  }, label), /* @__PURE__ */ React.createElement("div", {
    className: "flex items-center"
  }, /* @__PURE__ */ React.createElement("input", {
    type: "text",
    inputMode: unit === "K" ? "numeric" : "decimal",
    value: inputs[field],
    onChange: (e) => onChange(field, e.target.value),
    placeholder: "0",
    className: `w-full p-2 border rounded-lg focus:outline-none focus:ring-2 text-right font-mono text-lg bg-white ${colorClasses[color]}`
  }), /* @__PURE__ */ React.createElement("span", {
    className: "ml-2 text-gray-400 text-sm"
  }, unitConfig[unit].label)));
  var App = () => {
    const UNIT_CONFIG = {
      M: { step: 0.1, maxDigits: 99, label: "M" },
      K: { step: 100, maxDigits: 10, label: "K" }
    };
    const [teamName, setTeamName] = useState("");
    const [currentCash, setCurrentCash] = useState(15);
    const [turn, setTurn] = useState(1);
    const [history, setHistory] = useState([]);
    const [unit, setUnit] = useState("M");
    const hasLoadedRef = useRef(false);
    const prevUnitRef = useRef("M");
    const INPUT_FIELDS = [
      "salary",
      "rentIn",
      "tradeIn",
      "etcIn",
      "invest",
      "rentOut",
      "tradeOut",
      "donation",
      "fine"
    ];
    const initialInputs = {
      salary: "",
      rentIn: "",
      tradeIn: "",
      etcIn: "",
      invest: "",
      rentOut: "",
      tradeOut: "",
      donation: "",
      fine: ""
    };
    const [inputs, setInputs] = useState(initialInputs);
    const formatInputForUnit = (valueInM, activeUnit) => {
      if (!valueInM)
        return "";
      const displayValue = activeUnit === "M" ? valueInM : valueInM * 1000;
      if (activeUnit === "M") {
        return displayValue % 1 === 0 ? displayValue.toString() : displayValue.toFixed(1);
      }
      return Math.round(displayValue).toString();
    };
    const parseInputValue = (value, activeUnit) => {
      if (value === "")
        return { valueInM: 0, isValid: true };
      const normalized = value.replace(/,/g, "");
      if (!/^\d*\.?\d*$/.test(normalized)) {
        return { valueInM: 0, isValid: false };
      }
      const numericValue = parseFloat(normalized);
      if (Number.isNaN(numericValue) || numericValue < 0) {
        return { valueInM: 0, isValid: false };
      }
      if (activeUnit === "M") {
        const rounded = Math.round(numericValue * 10) / 10;
        const isValid = Math.abs(rounded - numericValue) < 0.000000001;
        return { valueInM: rounded, isValid };
      }
      if (!Number.isInteger(numericValue) || numericValue % 100 !== 0) {
        return { valueInM: numericValue / 1000, isValid: false };
      }
      return { valueInM: numericValue / 1000, isValid: true };
    };
    const parsedInputs = Object.fromEntries(INPUT_FIELDS.map((field) => [field, parseInputValue(inputs[field], unit)]));
    const getSafeValue = (field) => parsedInputs[field].isValid ? parsedInputs[field].valueInM : 0;
    const totalIncome = getSafeValue("salary") + getSafeValue("rentIn") + getSafeValue("tradeIn") + getSafeValue("etcIn");
    const totalExpense = getSafeValue("invest") + getSafeValue("rentOut") + getSafeValue("tradeOut") + getSafeValue("donation") + getSafeValue("fine");
    const turnProfit = totalIncome - totalExpense;
    useEffect(() => {
      const storedState = loadSettlementState();
      if (storedState) {
        const storedUnit = storedState.unit ?? "M";
        const storedInputs = storedState.inputs ?? {};
        setTeamName(storedState.teamName ?? "");
        setCurrentCash(storedState.currentCash ?? 15);
        setTurn(storedState.turn ?? 1);
        setHistory(Array.isArray(storedState.history) ? storedState.history : []);
        setUnit(storedUnit);
        setInputs({
          salary: typeof storedInputs.salary === "number" ? formatInputForUnit(storedInputs.salary, storedUnit) : storedInputs.salary ?? "",
          rentIn: typeof storedInputs.rentIn === "number" ? formatInputForUnit(storedInputs.rentIn, storedUnit) : storedInputs.rentIn ?? "",
          tradeIn: typeof storedInputs.tradeIn === "number" ? formatInputForUnit(storedInputs.tradeIn, storedUnit) : storedInputs.tradeIn ?? "",
          etcIn: typeof storedInputs.etcIn === "number" ? formatInputForUnit(storedInputs.etcIn, storedUnit) : storedInputs.etcIn ?? "",
          invest: typeof storedInputs.invest === "number" ? formatInputForUnit(storedInputs.invest, storedUnit) : storedInputs.invest ?? "",
          rentOut: typeof storedInputs.rentOut === "number" ? formatInputForUnit(storedInputs.rentOut, storedUnit) : storedInputs.rentOut ?? "",
          tradeOut: typeof storedInputs.tradeOut === "number" ? formatInputForUnit(storedInputs.tradeOut, storedUnit) : storedInputs.tradeOut ?? "",
          donation: typeof storedInputs.donation === "number" ? formatInputForUnit(storedInputs.donation, storedUnit) : storedInputs.donation ?? "",
          fine: typeof storedInputs.fine === "number" ? formatInputForUnit(storedInputs.fine, storedUnit) : storedInputs.fine ?? ""
        });
      }
      hasLoadedRef.current = true;
    }, []);
    useEffect(() => {
      if (!hasLoadedRef.current)
        return;
      saveSettlementState({
        teamName,
        currentCash,
        turn,
        history,
        inputs,
        unit
      });
    }, [teamName, currentCash, turn, history, inputs, unit]);
    useEffect(() => {
      const prevUnit = prevUnitRef.current;
      if (prevUnit === unit)
        return;
      setInputs((prev) => {
        const updated = { ...prev };
        INPUT_FIELDS.forEach((field) => {
          if (prev[field] === "") {
            updated[field] = "";
            return;
          }
          const parsed = parseInputValue(prev[field], prevUnit);
          if (parsed.isValid) {
            updated[field] = formatInputForUnit(parsed.valueInM, unit);
          }
        });
        return updated;
      });
      prevUnitRef.current = unit;
    }, [unit]);
    const formatAmount = (valueInM) => {
      const multiplier = unit === "M" ? 1 : 1000;
      const rawValue = valueInM * multiplier;
      const rounded = unit === "M" ? Math.round(rawValue * 10) / 10 : Math.round(rawValue);
      const hasDecimal = rounded % 1 !== 0;
      return rounded.toLocaleString(undefined, {
        minimumFractionDigits: hasDecimal ? 1 : 0,
        maximumFractionDigits: unit === "M" ? 1 : 0
      });
    };
    const setInputValueInM = (field, valueInM) => {
      setInputs((prev) => ({
        ...prev,
        [field]: formatInputForUnit(valueInM, unit)
      }));
    };
    const handleInputChange = (field, value) => {
      setInputs((prev) => ({
        ...prev,
        [field]: value
      }));
    };
    const finishTurn = () => {
      const invalidFields = INPUT_FIELDS.filter((field) => !parsedInputs[field].isValid);
      if (invalidFields.length > 0) {
        window.alert(`입력값을 확인해주세요.
M 단위는 0.1 단위, K 단위는 100 단위로 입력 가능합니다.`);
        return;
      }
      if (totalIncome === 0 && totalExpense === 0) {
        if (!window.confirm("수입/지출 내역이 없습니다. 이대로 턴을 넘기시겠습니까? ")) {
          return;
        }
      }
      const newBalance = currentCash + turnProfit;
      const inputsInM = Object.fromEntries(INPUT_FIELDS.map((field) => [field, parsedInputs[field].valueInM]));
      const turnData = {
        id: Date.now(),
        turn,
        income: totalIncome,
        expense: totalExpense,
        profit: turnProfit,
        balance: newBalance,
        details: inputsInM
      };
      setHistory([turnData, ...history]);
      setCurrentCash(newBalance);
      setTurn(turn + 1);
      setInputs(initialInputs);
    };
    const resetGame = () => {
      if (window.confirm("모든 기록을 지우고 게임을 처음부터 시작할까요?")) {
        setTurn(1);
        setCurrentCash(15);
        setHistory([]);
        setInputs(initialInputs);
      }
    };
    const clearInputs = () => {
      setInputs(initialInputs);
    };
    const undoLastTurn = () => {
      if (history.length === 0)
        return;
      if (!window.confirm("마지막 턴 기록을 삭제하고 되돌리겠습니까?"))
        return;
      const lastTurn = history[0];
      const prevHistory = history.slice(1);
      setHistory(prevHistory);
      setCurrentCash(lastTurn.balance - lastTurn.profit);
      setTurn(lastTurn.turn);
    };
    const colorClasses = {
      blue: "border-blue-200 focus:ring-blue-500 text-blue-700",
      red: "border-red-200 focus:ring-red-500 text-red-700"
    };
    return /* @__PURE__ */ React.createElement("div", {
      className: "min-h-full bg-gray-100 p-3 sm:p-4 w-full max-w-none sm:max-w-md mx-auto font-sans rounded-2xl border border-gray-100"
    }, /* @__PURE__ */ React.createElement("header", {
      className: "bg-white rounded-2xl p-6 shadow-sm mb-4 border border-gray-200"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "flex justify-between items-start mb-4"
    }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("input", {
      type: "text",
      placeholder: "조 이름 입력",
      className: "text-lg font-bold text-gray-800 placeholder-gray-300 focus:outline-none bg-transparent w-32",
      value: teamName,
      onChange: (e) => setTeamName(e.target.value)
    }), /* @__PURE__ */ React.createElement("p", {
      className: "text-xs text-gray-400"
    }, "모노폴리 손익계산기")), /* @__PURE__ */ React.createElement("button", {
      onClick: resetGame,
      className: "text-gray-400 hover:text-red-500",
      "aria-label": "정산 초기화"
    }, /* @__PURE__ */ React.createElement("i", {
      className: "fa-solid fa-rotate-left"
    }))), /* @__PURE__ */ React.createElement("div", {
      className: "text-center"
    }, /* @__PURE__ */ React.createElement("p", {
      className: "text-sm text-gray-500 mb-1"
    }, "현재 보유 자산 "), /* @__PURE__ */ React.createElement("div", {
      className: "text-5xl font-black text-blue-600 tracking-tight flex justify-center items-baseline"
    }, formatAmount(currentCash), " ", /* @__PURE__ */ React.createElement("span", {
      className: "text-2xl ml-1 text-blue-400"
    }, unit))), /* @__PURE__ */ React.createElement("div", {
      className: "mt-3 flex justify-center"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "inline-flex rounded-full bg-gray-100 p-1"
    }, ["M", "K"].map((value) => /* @__PURE__ */ React.createElement("button", {
      key: value,
      onClick: () => setUnit(value),
      className: `px-3 py-1 text-xs font-bold rounded-full transition ${unit === value ? "bg-blue-600 text-white shadow" : "text-gray-500 hover:text-gray-700"}`
    }, value, " 단위로 보기"))))), /* @__PURE__ */ React.createElement("div", {
      className: "bg-white rounded-2xl shadow-lg border border-blue-100 overflow-hidden mb-6"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "bg-blue-600 text-white p-3 flex justify-between items-center"
    }, /* @__PURE__ */ React.createElement("h2", {
      className: "font-bold text-lg flex items-center"
    }, /* @__PURE__ */ React.createElement("span", {
      className: "bg-white text-blue-600 text-xs px-2 py-1 rounded-full mr-2 font-black"
    }, "TURN ", turn), "이번 턴 기록"), /* @__PURE__ */ React.createElement("span", {
      className: "text-xs opacity-80"
    }, "단위: ", unit, " (1M=1000K)")), /* @__PURE__ */ React.createElement("div", {
      className: "p-4"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "grid grid-cols-2 gap-4"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "bg-blue-50 p-3 rounded-xl"
    }, /* @__PURE__ */ React.createElement("h3", {
      className: "text-blue-700 font-bold mb-3 flex items-center text-sm border-b border-blue-200 pb-1"
    }, /* @__PURE__ */ React.createElement("i", {
      className: "fa-solid fa-arrow-trend-up mr-1"
    }), " 수입"), /* @__PURE__ */ React.createElement("div", {
      className: "mb-3"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "flex justify-between items-end mb-1"
    }, /* @__PURE__ */ React.createElement("label", {
      className: "text-xs font-bold text-gray-500"
    }, "월급"), /* @__PURE__ */ React.createElement("button", {
      onClick: () => setInputValueInM("salary", 2),
      className: "text-[10px] bg-blue-200 text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-300"
    }, "+2M")), /* @__PURE__ */ React.createElement("div", {
      className: "flex items-center"
    }, /* @__PURE__ */ React.createElement("input", {
      type: "text",
      inputMode: unit === "K" ? "numeric" : "decimal",
      value: inputs.salary,
      onChange: (e) => handleInputChange("salary", e.target.value),
      className: "w-full p-2 border border-blue-200 rounded-lg text-right font-mono text-blue-700",
      placeholder: "0"
    }), /* @__PURE__ */ React.createElement("span", {
      className: "ml-2 text-gray-400 text-sm"
    }, UNIT_CONFIG[unit].label))), /* @__PURE__ */ React.createElement(InputField, {
      label: "통행료 수입",
      field: "rentIn",
      color: "blue",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    }), /* @__PURE__ */ React.createElement(InputField, {
      label: "사업 매각",
      field: "tradeIn",
      color: "blue",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    }), /* @__PURE__ */ React.createElement(InputField, {
      label: "복불복 카드",
      field: "etcIn",
      color: "blue",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    })), /* @__PURE__ */ React.createElement("div", {
      className: "bg-red-50 p-3 rounded-xl"
    }, /* @__PURE__ */ React.createElement("h3", {
      className: "text-red-700 font-bold mb-3 flex items-center text-sm border-b border-red-200 pb-1"
    }, /* @__PURE__ */ React.createElement("i", {
      className: "fa-solid fa-arrow-trend-down mr-1"
    }), " 지출"), /* @__PURE__ */ React.createElement(InputField, {
      label: "사업 투자 비용",
      field: "invest",
      color: "red",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    }), /* @__PURE__ */ React.createElement(InputField, {
      label: "통행료 지출",
      field: "rentOut",
      color: "red",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    }), /* @__PURE__ */ React.createElement("div", {
      className: "mb-2"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "flex justify-between items-end mb-1"
    }, /* @__PURE__ */ React.createElement("label", {
      className: "text-xs font-bold text-gray-500"
    }, "사회공헌"), /* @__PURE__ */ React.createElement("button", {
      onClick: () => setInputValueInM("donation", 1),
      className: "text-[10px] bg-red-200 text-red-700 px-1.5 py-0.5 rounded hover:bg-red-300"
    }, "-1M")), /* @__PURE__ */ React.createElement("div", {
      className: "flex items-center"
    }, /* @__PURE__ */ React.createElement("input", {
      type: "text",
      inputMode: unit === "K" ? "numeric" : "decimal",
      value: inputs.donation,
      onChange: (e) => handleInputChange("donation", e.target.value),
      className: "w-full p-2 border border-red-200 rounded-lg text-right font-mono text-red-700",
      placeholder: "0"
    }), /* @__PURE__ */ React.createElement("span", {
      className: "ml-2 text-gray-400 text-sm"
    }, UNIT_CONFIG[unit].label))), /* @__PURE__ */ React.createElement(InputField, {
      label: "손실 발생",
      field: "fine",
      color: "red",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    }), /* @__PURE__ */ React.createElement(InputField, {
      label: "복불복 카드",
      field: "tradeOut",
      color: "red",
      unit,
      inputs,
      onChange: handleInputChange,
      unitConfig: UNIT_CONFIG,
      colorClasses
    }))), /* @__PURE__ */ React.createElement("div", {
      className: "mt-4 p-3 bg-gray-800 rounded-xl text-white flex justify-between items-center shadow-lg"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "text-sm text-gray-400"
    }, /* @__PURE__ */ React.createElement("span", {
      className: "text-blue-400"
    }, "+", formatAmount(totalIncome)), " /", " ", /* @__PURE__ */ React.createElement("span", {
      className: "text-red-400"
    }, "-", formatAmount(totalExpense))), /* @__PURE__ */ React.createElement("div", {
      className: "text-right"
    }, /* @__PURE__ */ React.createElement("span", {
      className: "text-xs text-gray-400 block"
    }, "이번 턴 손익"), /* @__PURE__ */ React.createElement("span", {
      className: `text-xl font-bold ${turnProfit >= 0 ? "text-green-400" : "text-red-400"}`
    }, turnProfit > 0 ? "+" : "", formatAmount(turnProfit), " ", unit))), /* @__PURE__ */ React.createElement("div", {
      className: "mt-3 grid grid-cols-2 gap-3"
    }, /* @__PURE__ */ React.createElement("button", {
      onClick: clearInputs,
      className: "w-full bg-white border border-gray-200 text-gray-500 font-bold py-3 rounded-xl shadow-sm transition hover:text-gray-700 hover:border-gray-300 flex items-center justify-center"
    }, /* @__PURE__ */ React.createElement("i", {
      className: "fa-solid fa-eraser mr-2"
    }), " 입력 지우기"), /* @__PURE__ */ React.createElement("button", {
      onClick: finishTurn,
      className: "w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl shadow-md transition flex items-center justify-center"
    }, /* @__PURE__ */ React.createElement("i", {
      className: "fa-solid fa-floppy-disk mr-2"
    }), " 턴 종료 및 저장")))), /* @__PURE__ */ React.createElement("div", {
      className: "space-y-3"
    }, /* @__PURE__ */ React.createElement("h3", {
      className: "font-bold text-gray-500 text-sm flex items-center px-2"
    }, /* @__PURE__ */ React.createElement("i", {
      className: "fa-regular fa-clock mr-2"
    }), " 지난 턴 기록", history.length > 0 && /* @__PURE__ */ React.createElement("button", {
      onClick: undoLastTurn,
      className: "ml-auto text-xs text-red-400 underline"
    }, "마지막 턴 취소")), history.length === 0 ? /* @__PURE__ */ React.createElement("div", {
      className: "text-center py-8 text-gray-400 bg-white rounded-xl border border-dashed border-gray-300"
    }, "아직 기록된 내용이 없습니다.", /* @__PURE__ */ React.createElement("br", null), "게임을 시작해보세요!") : history.map((record) => /* @__PURE__ */ React.createElement("div", {
      key: record.id,
      className: "bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex justify-between items-center"
    }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", {
      className: "flex items-center gap-2 mb-1"
    }, /* @__PURE__ */ React.createElement("span", {
      className: "bg-gray-100 text-gray-600 text-xs font-bold px-2 py-0.5 rounded"
    }, "TURN ", record.turn), /* @__PURE__ */ React.createElement("span", {
      className: `text-sm font-bold ${record.profit >= 0 ? "text-blue-600" : "text-red-500"}`
    }, record.profit > 0 ? "+" : "", formatAmount(record.profit), " ", unit)), /* @__PURE__ */ React.createElement("div", {
      className: "text-xs text-gray-400"
    }, "수입 ", formatAmount(record.income), " / 지출", " ", formatAmount(record.expense))), /* @__PURE__ */ React.createElement("div", {
      className: "text-right"
    }, /* @__PURE__ */ React.createElement("div", {
      className: "text-xs text-gray-400"
    }, "잔액"), /* @__PURE__ */ React.createElement("div", {
      className: "font-bold text-gray-800 text-lg"
    }, formatAmount(record.balance), " ", unit))))), /* @__PURE__ */ React.createElement("div", {
      className: "mt-8 text-center pb-8"
    }, /* @__PURE__ */ React.createElement("p", {
      className: "text-xs text-gray-400"
    }, "* 실제 카드 결제기에는 턴이 끝난 후", /* @__PURE__ */ React.createElement("br", null), "최종 계산된 금액만 입력하면 됩니다.")));
  };
  ReactDOM.createRoot(document.getElementById("settlement-app")).render(/* @__PURE__ */ React.createElement(App, null));
})();
