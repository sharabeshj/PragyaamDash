import {
    defaultFont,
    successColor,
    warningColor
  } from "../../frontend";
  import tooltipStyle from "../tooltipStyle";
  import checkAndRadioStyle from "../checkboxAndRadioStyle";
  const tasksStyle = {
    ...tooltipStyle,
    ...checkAndRadioStyle,
    table: {
      marginBottom: "0",
      overflow: "visible"
    },
    tableRow: {
      position: "relative",
      borderBottom: "1px solid #dddddd"
    },
    tableActions: {
      display: "flex",
      border: "none",
      padding: "12px 8px !important",
      verticalAlign: "middle"
    },
    tableCell: {
      ...defaultFont,
      padding: "8px",
      verticalAlign: "middle",
      border: "none",
      lineHeight: "1.42857143",
      fontSize: "14px"
    },
    tableActionButton: {
      width: "27px",
      height: "27px"
    },
    tableActionButtonIcon: {
      width: "17px",
      height: "17px"
    },
    bL: {
      backgroundColor: "transparent",
      color: warningColor,
      boxShadow: "none"
    },
    fL: {
      backgroundColor: "transparent",
      color: successColor,
      boxShadow: "none"
    }
  };
  export default tasksStyle;
  