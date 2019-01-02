import React from 'react';
import PropTypes from 'prop-types';
import { NavLink } from 'react-router-dom';
import cx from "classnames";
import PerfectScrollbar from "perfect-scrollbar";

import withStyles from "@material-ui/core/styles/withStyles";
import Drawer from "@material-ui/core/Drawer";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemIcon from "@material-ui/core/ListItemIcon";
import ListItemText from "@material-ui/core/ListItemText";
import Hidden from "@material-ui/core/Hidden";
import Collapse from "@material-ui/core/Collapse";
import Icon from "@material-ui/core/Icon";

import HeaderLinks from '../Header/HeaderLinks';

import sidebarStyle from '../../assets/jss/frontend/components/sidebarStyle';

var ps;

class SidebarWrapper extends React.Component {
  componentDidMount() {
    if (navigator.platform.indexOf("Win") > -1) {
      ps = new PerfectScrollbar(this.refs.sidebarWrapper, {
        suppressScrollX: true,
        suppressScrollY: false
      });
    }
  }
  componentWillUnmount() {
    if (navigator.platform.indexOf("Win") > -1) {
      ps.destroy();
    }
  }
  render() {
    const { className, headerLinks, links } = this.props;
    return (
      <div className={className} ref="sidebarWrapper">
        {headerLinks}
        {links}
      </div>
    );
  }
}

class Sidebar extends React.Component {
    constructor(props){
        super(props);
        this.state = {
            miniActive : true,
            openReports : this.activeRoute("/reports"),
            openDatasets : this.activeRoute("/datasets")
        }
    }
    activeRoute(routeName) {
        return this.props.location.pathname.indexOf(routeName) > -1 ? true : false;
    }
    openCollapse(collapse){
        var st={}
        st[collapse] = !this.state[collapse]
        this.setState(st);
    }
    render(){
        const { 
            classes, 
            color, 
            logo, 
            image,
            routes,
            bgColor,
            logoText
        } = this.props;
    
        let links = (
            <List className = {classes.list}>
                {routes.map((prop,key) => {
                    if(prop.redirect) return null;
                    if  (prop.collapse) {
                        const navLinkClasses =
                          classes.itemLink +
                          " " +
                          cx({
                            [" " + classes.collapseActive]: this.activeRoute(prop.path)
                          });
                        const itemText =
                          classes.itemText +
                          " " +
                          cx({
                            [classes.itemTextMini]:
                              this.props.miniActive && this.state.miniActive,
                          });
                        const collapseItemText =
                          classes.collapseItemText +
                          " " +
                          cx({
                            [classes.collapseItemTextMini]:
                              this.props.miniActive && this.state.miniActive,
                          });
                        const itemIcon = classes.itemIcon;
                        const caret = classes.caret;
                        return (
                          <ListItem key={key} className={classes.item}>
                            <NavLink
                              to={"#"}
                              className={navLinkClasses}
                              onClick={() => this.openCollapse(prop.state)}
                            >
                              <ListItemIcon className={itemIcon}>
                                {typeof prop.icon === "string" ? (
                                  <Icon>{prop.icon}</Icon>
                                ) : (
                                  <prop.icon />
                                )}
                              </ListItemIcon>
                              <ListItemText
                                primary={prop.name}
                                secondary={
                                  <b
                                    className={
                                      caret +
                                      " " +
                                      (this.state[prop.state] ? classes.caretActive : "")
                                    }
                                  />
                                }
                                disableTypography={true}
                                className={itemText}
                              />
                            </NavLink>
                            <Collapse in={this.state[prop.state]} unmountOnExit>
                              <List className={classes.list + " " + classes.collapseList}>
                                {prop.views.map((prop, key) => {
                                  if (prop.redirect) {
                                    return null;
                                  }
                                  const navLinkClasses =
                                    classes.collapseItemLink +
                                    " " +
                                    cx({
                                      [" " + classes[color]]: this.activeRoute(prop.path)
                                    });
                                  const collapseItemMini = classes.collapseItemMini;
                                  return (
                                    <ListItem key={key} className={classes.collapseItem}>
                                      <NavLink to={prop.path} className={navLinkClasses}>
                                        <span className={collapseItemMini}>
                                          {prop.mini}
                                        </span>
                                        <ListItemText
                                          primary={prop.name}
                                          disableTypography={true}
                                          className={collapseItemText}
                                        />
                                      </NavLink>
                                    </ListItem>
                                  );
                                })}
                              </List>
                            </Collapse>
                          </ListItem>
                        );
                      }
                    const navLinkClasses =
                        classes.itemLink +
                        " " +
                        cx({
                        [" " + classes[color]]: this.activeRoute(prop.path)
                        });
                    const itemText =
                        classes.itemText +
                        " " +
                        cx({
                        [classes.itemTextMini]:
                            this.props.miniActive && this.state.miniActive,
                        });
                    const itemIcon = classes.itemIcon
                    return (
                        <ListItem key={key} className={classes.item}>
                            <NavLink to={prop.path} className={navLinkClasses}>
                                <ListItemIcon className={itemIcon}>
                                {typeof prop.icon === "string" ? (
                                    <Icon>{prop.icon}</Icon>
                                ) : (
                                    <prop.icon />
                                )}
                                </ListItemIcon>
                                <ListItemText
                                primary={prop.name}
                                disableTypography={true}
                                className={itemText}
                                />
                            </NavLink>
                        </ListItem>
                    );
                })}
            </List>
        );
        const logoNormal =
            classes.logoNormal +
            " " +
            cx({
                [classes.logoNormalSidebarMini]:
                this.props.miniActive && this.state.miniActive,
            });
            const logoMini = classes.logoMini;
            const logoClasses =
            classes.logo +
            " " +
            cx({
                [classes.whiteAfter]: bgColor === "white"
            });
            var brand = (
            <div className={logoClasses}>
                <a href="http://pragyaamf.mysnippt.com/" className={logoMini}>
                <img src={logo} alt="logo" className={classes.img} />
                </a>
                <a href="http://pragyaamf.mysnippt.com/" className={logoNormal}>
                {logoText}
                </a>
            </div>
            );
            const drawerPaper =
            classes.drawerPaper +
            " " +
            cx({
                [classes.drawerPaperMini]:
                this.props.miniActive && this.state.miniActive,
            });
            const sidebarWrapper =
            classes.sidebarWrapper +
            " " +
            cx({
                [classes.drawerPaperMini]:
                this.props.miniActive && this.state.miniActive,
                [classes.sidebarWrapperWithPerfectScrollbar]:
                navigator.platform.indexOf("Win") > -1
            });
        return (
            <div ref="mainPanel">
                <Hidden mdUp implementation = "css">
                    <Drawer
                        variant = "temporary"
                        anchor = "right"
                        open = {this.props.open}
                        classes = {{
                            paper :  drawerPaper + " " + classes[bgColor + "Background"]
                        }}
                        onClose = {this.props.handleDrawerToggle}
                        ModalProps = {{
                            keepMounted : true
                        }}
                    >
                        {brand}
                        <SidebarWrapper
                            className={sidebarWrapper}
                            headerLinks={<HeaderLinks/>}
                            links={links}  
                        />
                        {image !== undefined ? (
                            <div
                                className={classes.background}
                                style={{ backgroundImage: "url(" + image + ")" }}
                            />
                            ) : null}
                    </Drawer>
                </Hidden>
                <Hidden smDown implementation = "css">
                    <Drawer
                        onMouseOver={() => this.setState({ miniActive: false })}
                        onMouseOut={() => this.setState({ miniActive: true })}
                        anchor = "left"
                        variant = "permanent"
                        open
                        classes = {{
                            paper : drawerPaper + " " + classes[bgColor + "Background"]
                        }}
                    >
                        {brand}
                        <SidebarWrapper
                            className={sidebarWrapper}
                            links={links}
                        />
                        {image !== undefined ? (
                        <div
                            className={classes.background}
                            style={{ backgroundImage: "url(" + image + ")" }}
                        />
                        ) : null}
                    </Drawer>
                </Hidden>
            </div>
        );
    }
    
};

Sidebar.defaultProps = {
    bgColor : "blue"
};

Sidebar.propTypes = {
    classes: PropTypes.object.isRequired,
    bgColor: PropTypes.oneOf(["white", "black", "blue"]),
    color: PropTypes.oneOf([
        "white",
        "red",
        "orange",
        "green",
        "blue",
        "purple",
        "rose"
    ]),
    logo: PropTypes.string,
    logoText: PropTypes.string,
    image: PropTypes.string,
    routes: PropTypes.arrayOf(PropTypes.object)
};

export default withStyles(sidebarStyle)(Sidebar);