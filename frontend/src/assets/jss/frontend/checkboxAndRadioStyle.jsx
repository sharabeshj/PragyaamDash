import { successColor } from "../frontend";

const checkboxAdnRadioStyle = {
  checked: {
    color: successColor + "!important"
  },
  checkedIcon: {
    width: "20px",
    height: "20px",
    border: "1px solid rgba(0, 0, 0, .54)",
    borderRadius: "3px"
  },
  uncheckedIcon: {
    width: "0px",
    height: "0px",
    padding: "10px",
    border: "1px solid rgba(0, 0, 0, .54)",
    borderRadius: "3px"
  },
  radio: {
    color: successColor + "!important",
  },
  radioChecked: {
    width: "20px",
    height: "20px",
    border: "1px solid " + successColor,
    borderRadius: "50%"
  },
  radioUnchecked: {
    width: "0px",
    height: "0px",
    padding: "10px",
    border: "1px solid rgba(0, 0, 0, .54)",
    borderRadius: "50%"
  }
};

export default checkboxAdnRadioStyle;
