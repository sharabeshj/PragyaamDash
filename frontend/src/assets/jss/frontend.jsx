const drawerWidth = 260;
const sidebarWidth = 72;

const transition = {
    transition : " all 0.33s cubic-beizer(0.685,0.0473,0.346,1)"
};

const container = {
    paddingRight : "15px",
    paddingLeft : "15px",
    marginRight : "auto",
    marginLeft : "auto"
};

const boxShadow = {
    boxShadow : 
        "0 10px 30px -12px rgba(0,0,0,0.42), 0 4px 25px 0px rgba(0, 0, 0, 0.12), 0 8px 10px -5px rgba(0,0,0,0.2)"
};

// const card = {
//     display : "inline-block",
//     position : "relative",
//     width : "100%",
//     margin : "25px 0",
//     boxShadow : "0 1px 4px 0 rgba(0, 0, 0, 0.14)",
//     borderRadius : "3px",
//     color : "rgba(0, 0, 0, 0.87)",
//     background : "#fff"
// }

const defaultFont = {
    fontFamily : '"Roboto", "Helvetica", "Arial", sans-serif',
    fontWeight : "300",
    lineHeight : "1.5em"
};

const primaryColor = "#9c27b0";
const warningColor = "#ff9800";
const dangerColor = "#f44336";
const successColor = "#4caf50";
const infoColor = "#00acc1";
const roseColor = "#e91e63";
const grayColor = "#999999";

const primaryBoxShadow = {
  boxShadow:
    "0 12px 20px -10px rgba(156, 39, 176, 0.28), 0 4px 20px 0px rgba(0, 0, 0, 0.12), 0 7px 8px -5px rgba(156, 39, 176, 0.2)"
};
const infoBoxShadow = {
  boxShadow:
    "0 12px 20px -10px rgba(0, 188, 212, 0.28), 0 4px 20px 0px rgba(0, 0, 0, 0.12), 0 7px 8px -5px rgba(0, 188, 212, 0.2)"
};
const successBoxShadow = {
  boxShadow:
    "0 12px 20px -10px rgba(76, 175, 80, 0.28), 0 4px 20px 0px rgba(0, 0, 0, 0.12), 0 7px 8px -5px rgba(76, 175, 80, 0.2)"
};
const warningBoxShadow = {
  boxShadow:
    "0 12px 20px -10px rgba(255, 152, 0, 0.28), 0 4px 20px 0px rgba(0, 0, 0, 0.12), 0 7px 8px -5px rgba(255, 152, 0, 0.2)"
};
const dangerBoxShadow = {
  boxShadow:
    "0 12px 20px -10px rgba(244, 67, 54, 0.28), 0 4px 20px 0px rgba(0, 0, 0, 0.12), 0 7px 8px -5px rgba(244, 67, 54, 0.2)"
};
const roseBoxShadow = {
  boxShadow:
    "0 4px 20px 0px rgba(0, 0, 0, 0.14), 0 7px 10px -5px rgba(233, 30, 99, 0.4)"
};

const defaultBoxShadow = {
    border: "0",
    borderRadius: "3px",
    boxShadow:
      "0 10px 20px -12px rgba(0, 0, 0, 0.42), 0 3px 20px 0px rgba(0, 0, 0, 0.12), 0 8px 10px -5px rgba(0, 0, 0, 0.2)",
    padding: "10px 0",
    transition: "all 150ms ease 0s"
  };
  
  const title = {
    color: "#3C4858",
    textDecoration: "none",
    fontWeight: "300",
    marginTop: "30px",
    marginBottom: "25px",
    minHeight: "32px",
    fontFamily: "'Roboto', 'Helvetica', 'Arial', sans-serif",
    "& small": {
      color: "#777",
      fontWeight: "400",
      lineHeight: "1"
    }
  };

  export {
    //variables
    sidebarWidth,
    drawerWidth,
    transition,
    container,
    boxShadow,
    defaultFont,
    primaryColor,
    warningColor,
    dangerColor,
    successColor,
    infoColor,
    roseColor,
    grayColor,
    primaryBoxShadow,
    infoBoxShadow,
    successBoxShadow,
    warningBoxShadow,
    dangerBoxShadow,
    roseBoxShadow,
    defaultBoxShadow,
    title
  };
  
  