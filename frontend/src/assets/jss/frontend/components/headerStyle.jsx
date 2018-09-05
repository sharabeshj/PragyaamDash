import {
    container,
    defaultFont,
    primaryColor,
    defaultBoxShadow,
    infoColor,
    successColor,
    warningColor,
    dangerColor
  } from "../../frontend";
  
  const headerStyle = theme => ({
    appBar: {
      backgroundColor: "white",
      boxShadow: " 1px 2px 5px #b3b3b3",
      borderBottom: "0",
      marginBottom: "0",
      position: "absolute",
      width: "100%",
      zIndex: "1029",
      color: "#555555",
      border: "0",
      borderRadius: "3px",
      padding: "10px 0",
      transition: "all 150ms ease 0s",
      minHeight: "50px",
      display: "block"
    },
    container: {
      ...container,
      height : '32px'
    },
    flex: {
      flex: 1
    },
    title: {
      ...defaultFont,
      lineHeight: "30px",
      fontSize: "18px",
      borderRadius: "3px",
      textTransform: "none",
      color: "inherit",
      "&:hover,&:focus": {
        background: "transparent"
      }
    },
    appResponsive: {
      top: "8px"
    },
    primary: {
      backgroundColor: primaryColor,
      color: "#FFFFFF",
      ...defaultBoxShadow
    },
    info: {
      backgroundColor: infoColor,
      color: "#FFFFFF",
      ...defaultBoxShadow
    },
    success: {
      backgroundColor: successColor,
      color: "#FFFFFF",
      ...defaultBoxShadow
    },
    warning: {
      backgroundColor: warningColor,
      color: "#FFFFFF",
      ...defaultBoxShadow
    },
    danger: {
      backgroundColor: dangerColor,
      color: "#FFFFFF",
      ...defaultBoxShadow
    }
  });
  
  export default headerStyle;
  