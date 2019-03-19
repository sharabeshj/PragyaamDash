import React from 'react';
import cx from 'classnames';
import PropTypes from 'prop-types';

import { withStyles } from '@material-ui/core/styles';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar'; 
import Hidden from '@material-ui/core/Hidden';

import Menu from '@material-ui/icons/Menu';
import MoreVert from "@material-ui/icons/MoreVert";
import ViewList from "@material-ui/icons/ViewList";

import HeaderLinks from './HeaderLinks';
import Button from '../CustomButtons/Button';

import headerStyle from '../../assets/jss/frontend/components/headerStyle';

function Header({ ...props }) {
    function makeBrand() {
      var name;
      props.routes.map((prop, key) => {
        if (prop.collapse) {
          prop.views.map((prop, key) => {
            if (prop.path === props.location.pathname) {
              name = prop.name;
            }
            return null;
          });
        }
        if (prop.path === props.location.pathname) {
          name = prop.name;
        }
        return null;
      });
      return name;
    }
    const { classes, color } = props;
    const appBarClasses = cx({
      [" " + classes[color]]: color
    });
    const sidebarMinimize = classes.sidebarMinimize;
    return (
      <AppBar className={classes.appBar + appBarClasses}>
        <Toolbar className={classes.container}>
          <Hidden smDown implementation="css">
            <div className={sidebarMinimize}>
              {props.miniActive ? (
                <Button
                  justIcon
                  round
                  color="white"
                  onClick={props.sidebarMinimize}
                >
                  <ViewList className={classes.sidebarMiniIcon} />
                </Button>
              ) : (
                <Button
                  justIcon
                  round
                  color="white"
                  onClick={props.sidebarMinimize}
                >
                  <MoreVert className={classes.sidebarMiniIcon} />
                </Button>
              )}
            </div>
          </Hidden>
          <div className={classes.flex}>

            <Button color="transparent" href="#" className={classes.title}>
              {makeBrand()}
            </Button>
          </div>
          <Hidden smDown implementation="css">
            <HeaderLinks />
          </Hidden>
          <Hidden mdUp implementation="css">
            <Button
              className={classes.appResponsive}
              color="transparent"
              justIcon
              aria-label="open drawer"
              onClick={props.handleDrawerToggle}
            >
              <Menu />
            </Button>
          </Hidden>
        </Toolbar>
      </AppBar>
    );
  }
  
  Header.propTypes = {
    classes: PropTypes.object.isRequired,
    color: PropTypes.oneOf(["primary", "info", "success", "warning", "danger"])
  };
  
  export default withStyles(headerStyle)(Header);
  