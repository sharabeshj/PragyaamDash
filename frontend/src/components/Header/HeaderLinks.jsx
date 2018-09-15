import React,{ Component } from 'react';
import classNames from 'classnames';

import { withStyles } from '@material-ui/core/styles';
import MenuItem from '@material-ui/core/MenuItem';
import MenuList from '@material-ui/core/MenuList';
import Grow from '@material-ui/core/Grow';
import Paper from '@material-ui/core/Paper';
import ClickAwayListener from '@material-ui/core/ClickAwayListener';
import Hidden from '@material-ui/core/Hidden';
import Poppers from '@material-ui/core/Popper';

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
        return (
            <div>
                <div className = {classes.searchWrapper}>
                    <CustomInput 
                        formControlProps = {{
                            classNames : classes.margin + " " + classes.search
                        }}
                        inputProps = {{
                            placeholder : "Search",
                            inputProps : {
                                "aria-label" : "Search"
                            }
                        }} 
                    />
                    <Button color = "simple" aria-label = "edit" justIcon round >
                        <HelpOutline />
                    </Button>
                </div>
                <div className = {classes.manager}>
                    <Button
                        buttonRef = { node => {
                            this.anchorEl = node;
                        }}
                        color = {window.innerWidth > 959 ? "transparent" : "white" }
                        justIcon = { window.innerWidth > 959}
                        simple = {!(window.innerWidth > 959)}
                        aria-owns = { open ? "menu-list-grow" : null}
                        aria-haspopup = "true"
                        onClick = { this.handleToggle }
                        className = { classes.buttonLink }
                    >
                        <Notifications className = {classes.icons}/>
                        <span className = {classes.Notifications}>5</span>
                        <Hidden
                            mdUp implementation = "css"
                        >
                            <p onClick = {this.handleClick } className = {classes.linkText}>
                                Notification
                            </p>
                        </Hidden>
                    </Button>
                    <Poppers
                        open = {open}
                        anchorEl = {this.anchorEl}
                        transition 
                        disablePortal
                        className = {
                            classNames({ [classes.popperClose]: !open }) + 
                            " " + 
                            classes.pooperNav
                        }                    
                    >
                        {({ TransitionProps, placement }) => (
                            <Grow
                                {...TransitionProps}
                                id = "menu-list-grow"
                                style = {{
                                    transformOrigin :
                                        placement === "bottom" ? "center top" : "center bottom"
                                }}
                            >
                                <Paper>
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
                    </Poppers>
                </div>
                <div className = {classes.manager}>
                    <Button
                        color = {window.innerWidth > 959 ? "transparent" : "white"}
                        simple
                        aria-label = "Person"
                        className = {classes.buttonLink}
                        onClick = {this.handleToggleU}
                    >
                        <Person className = {classes.icons}/>
                        <p className = {classes.linkText}>Name of Orgainsation</p>
                    </Button>
                    <Poppers
                        open = {uOpen}
                        anchorEl = {this.anchorEl}
                        transition 
                        disablePortal
                        className = {
                            classNames({ [classes.popperClose]: !open }) + 
                            " " + 
                            classes.pooperNav
                        }                    
                    >
                        {({ TransitionProps, placement }) => (
                            <Grow
                                {...TransitionProps}
                                id = "menu-list-grow"
                                style = {{
                                    transformOrigin :
                                        placement === "bottom" ? "center top" : "center bottom"
                                }}
                            >
                                <Paper>
                                    <ClickAwayListener onClickAway = {this.handleUClose}>
                                        <MenuList role = "menu">
                                            <MenuItem
                                                onClick = {this.handleUClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Mike John responded to your email                                            
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleUClose}
                                                className = {classes.dropdownItem}
                                            >
                                                You have 5 new tasks                                           
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleUClose}
                                                className = {classes.dropdownItem}
                                            >
                                                You're now friend with Andrew                                         
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleUClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Another Notification                                            
                                            </MenuItem>
                                            <MenuItem
                                                onClick = {this.handleUClose}
                                                className = {classes.dropdownItem}
                                            >
                                                Another One                                         
                                            </MenuItem>
                                        </MenuList>
                                    </ClickAwayListener>
                                </Paper>
                            </Grow>
                        )}
                    </Poppers>
                </div>
            </div>
        );
    }
}

export default withStyles(headerLinksStyle)(HeaderLinks);