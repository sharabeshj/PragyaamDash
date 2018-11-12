/* eslint-disable */
import React from 'react';
import PropTypes from 'prop-types';
import { Switch, Route, Redirect } from 'react-router-dom';
import { connect } from 'react-redux';

import PerfectScrollbar from 'perfect-scrollbar';
import '../../../node_modules/perfect-scrollbar/css/perfect-scrollbar.css';

import { withStyles } from '@material-ui/core/styles';

import Header from '../../components/Header/Header';
import Sidebar from '../../components/Sidebar/Sidebar';

import dashboardRoutes from "routes/dashboard.jsx";

import dashboardStyle from "../../assets/jss/frontend/layouts/dashboardStyle";

import { mobileResizeFunction, handleDrawerToggle, handleDrawerToggleOnUpdate } from '../../store/Actions/ActionCreator';

import logo from "assets/img/reactlogo.png";

const switchRoutes = (
  <Switch>
    {dashboardRoutes.map((prop, key) => {
      if (prop.redirect)
        return <Redirect from={prop.path} to={prop.to} key={key} />;
      return <Route path={prop.path} component={prop.component} key={key} />;
    })}
  </Switch>
);

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
      const ps = new PerfectScrollbar(this.refs.mainPanel);
    }
    window.addEventListener("resize", this.props.mobileResizeFunction);
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
    window.removeEventListener("resize", this.props.mobileResizeFunction);
  }
  render() {
    const { classes, ...rest } = this.props;
    const dashboardRoutes = this.dashboardRoutes;
    const logo = this.logo;
    console.log(dashboardRoutes);
    return (
      <div className={classes.wrapper}>
        <Sidebar
          routes={dashboardRoutes}
          logo={logo}
          handleDrawerToggle={this.props.handleDrawerToggle}
          open={this.props.mobileOpen}
          color="blue"
          {...rest}
        />
        <div className={classes.mainPanel} ref="mainPanel">
          <Header
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
  mobileOpen : state.drawer.mobileOpen
});

const mapDispatchToProps = dispatch => ({
  mobileResizeFunction : () => dispatch(mobileResizeFunction()),
  handleDrawerToggle : () => dispatch(handleDrawerToggle()),
  handleDrawerToggleOnUpdate : () => dispatch(handleDrawerToggleOnUpdate())
});

export default connect(mapStateToProps, mapDispatchToProps)(withStyles(dashboardStyle)(App));
