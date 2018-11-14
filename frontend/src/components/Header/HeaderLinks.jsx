import React,{ Component } from 'react';
import classNames from 'classnames';
import PropTypes from "prop-types";

import { withStyles } from '@material-ui/core/styles';
import MenuItem from '@material-ui/core/MenuItem';
import MenuList from '@material-ui/core/MenuList';
import Grow from '@material-ui/core/Grow';
import Paper from '@material-ui/core/Paper';
import ClickAwayListener from '@material-ui/core/ClickAwayListener';
import Hidden from '@material-ui/core/Hidden';
import Popper from '@material-ui/core/Popper';

import Notifications from '@material-ui/icons/Notifications';
import Person from '@material-ui/icons/Person';
import HelpOutline from '@material-ui/icons/HelpOutline'

import CustomInput from '../CustomInput/CustomInput';
import Button from '../CustomButtons/Button';

import headerLinksStyle from '../../assets/jss/frontend/components/headerLinksStyle';

class HeaderLinks extends Component {
    state = {
        open : false,
        uOpen : false
    };

    handleClick = () => {
        this.setState({ open: !this.state.open });
      };

    handleToggle = () => {
        this.setState(state => ({ open : !state.open, uOpen : false }));
    };
    handleToggleU = () => {
        this.setState(state => ({ uOpen : !state.uOpen, open : false }));
    }
    handleClose = event => {
        if(this.anchorEl.contains(event.target)){
            return;
        }

        this.setState({ open : false });
    };

    handleUClose = event => {
        if(this.anchorEl.contains(event.target)){
            return;
        }

        this.setState({ open : false });
    };
    render(){
        const { classes } = this.props;
        const { open,uOpen } = this.state;
        const searchButton = classes.top + " " + classes.searchButton;
        const dropdownItem = classNames(
            classes.dropdownItem,
            classes.primaryHover
          );
          const managerClasses = classNames({
            [classes.managerClasses]: true
          });
        return (
            <div>
                <div className = {classes.searchWrapper}>
                    <CustomInput 
                        formControlProps={{
                            className: classes.top + " " + classes.search
                          }}
                        inputProps = {{
                            placeholder : "Search",
                            inputProps : {
                                "aria-label" : "Search",
                                className: classes.searchInput
                            }
                        }} 
                    />
                    <Button color = "simple" aria-label = "edit" justIcon round className={searchButton}>
                        <HelpOutline 
                        className={classes.headerLinksSvg + " " + classes.searchIcon}
                        />
                    </Button>
                </div>
                <div className = {managerClasses}>
                    <Button
                        buttonRef = { node => {
                            this.anchorEl = node;
                        }}
                        color = {"transparent"}
                        justIcon
                        aria-label="Notifications"
                        aria-owns = { open ? "menu-list" : null}
                        aria-haspopup = "true"
                        onClick = { this.handleToggle }
                        className = { classes.buttonLink }
                    >
                        <Notifications
                            className={
                                classes.headerLinksSvg + " " + classes.links
                              }
                        />
                        <span className = {classes.Notifications}>5</span>
                        <Hidden
                            mdUp implementation = "css"
                        >
                            <span onClick = {this.handleClick } className = {classes.linkText}>
                                Notification
                            </span>
                        </Hidden>
                    </Button>
                    <Popper
                        open = {open}
                        anchorEl = {this.anchorEl}
                        transition 
                        disablePortal
                        placement="bottom"
                        className={classNames({
                            [classes.popperClose]: !open,
                            [classes.pooperResponsive]: true,
                            [classes.pooperNav]: true
                          })}                 
                    >
                        {({ TransitionProps, placement }) => (
                            <Grow
                                {...TransitionProps}
                                id = "menu-list"
                                style={{ transformOrigin: "0 0 0" }}
                            >
                                <Paper className={classes.dropdown}>
                                    <ClickAwayListener onClickAway = {this.handleClose}>
                                        <MenuList role = "menu">
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Mike John responded to your email                                            
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                You have 5 new tasks                                           
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                You're now friend with Andrew                                         
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Another Notification                                            
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Another One                                         
                                            </MenuItem>
                                        </MenuList>
                                    </ClickAwayListener>
                                </Paper>
                            </Grow>
                        )}
                    </Popper>
                </div>
                <div className = {managerClasses}>
                    <Button
                        buttonRef = { node => {
                            this.anchorEl = node;
                        }}
                        color = {"transparent"}
                        justIcon
                        aria-label="Person"
                        aria-owns = { open ? "menu-list" : null}
                        aria-haspopup = "true"
                        onClick = { this.handleToggleU }
                        className = { classes.buttonLink }
                    >
                        <Person
                            className={
                                classes.headerLinksSvg + " " + classes.links
                              }
                        />
                        <span className = {classes.linkText}>
                                Notification
                            </span>
                    </Button>
                    <Popper
                        open = {open}
                        anchorEl = {this.anchorEl}
                        transition 
                        disablePortal
                        placement="bottom"
                        className={classNames({
                            [classes.popperClose]: !open,
                            [classes.pooperResponsive]: true,
                            [classes.pooperNav]: true
                          })}                 
                    >
                        {({ TransitionProps, placement }) => (
                            <Grow
                                {...TransitionProps}
                                id = "menu-list"
                                style={{ transformOrigin: "0 0 0" }}
                            >
                                <Paper className={classes.dropdown}>
                                    <ClickAwayListener onClickAway = {this.handleUClose}>
                                        <MenuList role = "menu">
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Mike John responded to your email                                            
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                You have 5 new tasks                                           
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                You're now friend with Andrew                                         
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Another Notification                                            
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Another One                                         
                                            </MenuItem>
                                        </MenuList>
                                    </ClickAwayListener>
                                </Paper>
                            </Grow>
                        )}
                    </Popper>
                </div>
            </div>
        );
    }
}

HeaderLinks.propTypes = {
    classes : PropTypes.object.isRequired
};

export default withStyles(headerLinksStyle)(HeaderLinks);