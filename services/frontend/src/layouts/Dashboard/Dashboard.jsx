/* eslint-disable */
import React from 'react';
import PropTypes from 'prop-types';
import { Switch, Route, Redirect } from 'react-router-dom';
import { connect } from 'react-redux';
import cx from 'classnames';

import PerfectScrollbar from 'perfect-scrollbar';
import '../../../node_modules/perfect-scrollbar/css/perfect-scrollbar.css';

import { withStyles } from '@material-ui/core/styles';

import Header from '../../components/Header/Header';
import Sidebar from '../../components/Sidebar/Sidebar';

import dashboardRoutes from "routes/dashboardRoutes.jsx";

import dashboardStyle from "../../assets/jss/frontend/layouts/dashboardStyle";

import { mobileResizeFunction, handleDrawerToggle, handleDrawerToggleOnUpdate, handleMiniSidebarToggle } from '../../store/Actions/ActionCreator';

import logo from "assets/img/logo.png";
import image from "assets/img/sidebar-2.jpg";

const switchRoutes = (
  <Switch>
    {dashboardRoutes.map((prop, key) => {
      if (prop.redirect)
        return <Redirect from={prop.path} to={prop.to} key={key} />;
      if (prop.collapse)
        return prop.views.map((prop, key) => {
          return (
            <Route path={prop.path} component={prop.component} key={key} />
          );
        });
      return <Route path={prop.path} component={prop.component} key={key} />;
    })}
  </Switch>
);

var ps;

class App extends React.Component {
  constructor(props) {
    super(props);
    this.dashboardRoutes = dashboardRoutes;
    this.logo = logo;

  }
  
  getRoute() {
    return this.props.location.pathname !== "/maps";
  }
  componentDidMount() {
    if (navigator.platform.indexOf("Win") > -1) {
      ps = new PerfectScrollbar(this.refs.mainPanel, {
        suppressScrollX: true,
        suppressScrollY: false
      });
      document.body.style.overflow = "hidden";
    }
    window.addEventListener("resize", this.props.resizeFunction);
  }
  componentDidUpdate(e) {
    if (e.history.location.pathname !== e.location.pathname) {
      this.refs.mainPanel.scrollTop = 0;
      if (this.props.mobileOpen) {
        this.props.handleDrawerToggleOnUpdate()
      }
    }
  }
  componentWillUnmount() {
    if (navigator.platform.indexOf("Win") > -1) {
      ps.destroy();
    }
    window.removeEventListener("resize", this.resizeFunction);
  }
  render() {
    const { classes, ...rest } = this.props;
    const mainPanel = 
      classes.mainPanel +
      " " +
      cx({
        [classes.mainPanelSidebarMini]: this.props.miniActive,
        [classes.mainPanelWithPerfectScrollbar]:
          navigator.platform.indexOf("Win") > -1
      });
    const dashboardRoutes = this.dashboardRoutes;
    const logo = this.logo;
    console.log(dashboardRoutes);
    return (
      <div className={classes.wrapper}>
        <Sidebar
          routes={dashboardRoutes}
          logo={logo}
          logoText={"PragYaam"}
          image={image}
          handleDrawerToggle={this.props.handleDrawerToggle}
          open={this.props.mobileOpen}
          color="blue"
          bgColor="black"
          miniActive={this.props.miniActive}
          {...rest}
        />
        <div className={mainPanel} ref="mainPanel">
          <Header
            sidebarMinimize = {this.props.handleMiniSidebarToggle}
            miniActive = {this.props.miniActive}
            routes={dashboardRoutes}
            handleDrawerToggle={this.props.handleDrawerToggle}
            {...rest}
          />
          <div className = {classes.content}>
            <div className = {classes.container}>{switchRoutes}</div>
          </div>
        </div>
      </div>
    );
  }
}

App.propTypes = {
  classes: PropTypes.object.isRequired
};

const mapStateToProps = state => ({
  mobileOpen : state.drawer.mobileOpen,
  miniActive : state.drawer.miniActive
});

const mapDispatchToProps = dispatch => ({
  mobileResizeFunction : () => dispatch(mobileResizeFunction()),
  handleDrawerToggle : () => dispatch(handleDrawerToggle()),
  handleDrawerToggleOnUpdate : () => dispatch(handleDrawerToggleOnUpdate()),
  handleMiniSidebarToggle : () => dispatch(handleMiniSidebarToggle())
});

export default connect(mapStateToProps, mapDispatchToProps)(withStyles(dashboardStyle)(App));
