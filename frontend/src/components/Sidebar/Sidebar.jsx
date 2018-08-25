import React from 'react';
import classNames from 'classnames';
import PropTypes from 'prop-types';
import { NavLink } from 'react-router-dom';

import { withStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import Hidden from '@material-ui/core/Hidden';
import List from '@material-ui/core/List';
import ListItem from "@material-ui/core/ListItem";
import ListItemIcon from "@material-ui/core/ListItemIcon";

import HeaderLinks from '../Header/HeaderLinks';

import sidebarStyle from '../../assets/jss/frontend/components/sidebarStyle';

const Sidebar = ({ ...props }) => {
    function activeRoute(routeName) {
        return props.location.pathname.indexOf(routeName) > -1 ? true : false;
    }
    const { classes, color, logo, routes } = props;

    let links = (
        <List className = {classes.list}>
            {routes.map((prop,key) => {
                if(prop.redirect) return null;
                let activePro = " ";
                let listItemClasses = classNames({
                    [" " + classes[color]]: activeRoute(prop.path)
                });
                const whiteFontClasses = classNames({
                    [" " + classes.whiteFont]: activeRoute(prop.path)
                  });
                return (
                    <NavLink
                        to = {prop.path}
                        className = {activePro + classes.item}
                        activeClassName = "active"
                        key = {key}
                    >
                        <ListItem button className = {classes.itemLink + listItemClasses}>
                            <ListItemIcon className = {classes.item + whiteFontClasses}>
                                <prop.icon />
                            </ListItemIcon>
                        </ListItem>
                    </NavLink>
                );
            })}
        </List>
    );
    let brand = (
        <div className = {classes.logo}>
            <a href = "/" className = {classes.logoLink}>
                <div className = { classes.logoImage }>
                    <img src =  {logo} alt = "logo" className = {classes.img}/>
                </div>
            </a>
        </div>
    );
    return (
        <div>
            <Hidden mdUp implementation = "css">
                <Drawer
                    variant = "temporary"
                    anchor = "right"
                    open = {props.open}
                    classes = {{
                        paper :  classes.drawerPaper
                    }}
                    onClose = {props.handleDrawerToggle}
                    ModalProps = {{
                        keepMounted : true
                    }}
                >
                    {brand}
                    <div className = {classes.sidebarWrapper}>
                        <HeaderLinks />
                        {links}
                    </div>
                </Drawer>
            </Hidden>
            <Hidden smDown implementation = "css">
                <Drawer
                    anchor = "left"
                    variant = "permanent"
                    open
                    classes = {{
                        paper : classes.drawerPaper
                    }}
                >
                    {brand}
                    <div className = {classes.sidebarWrapper}>{links}</div>
                </Drawer>
            </Hidden>
        </div>
    );
};

Sidebar.propTypes = {
    classes: PropTypes.object.isRequired
};

export default withStyles(sidebarStyle)(Sidebar);