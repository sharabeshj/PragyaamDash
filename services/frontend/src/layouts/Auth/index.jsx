import React from 'react';
import PropTypes from 'prop-types';
import { Switch, Route, Redirect,withRouter } from 'react-router-dom';

import withStyles from '@material-ui/core/styles/withStyles';

import AuthNavbar from '../../components/AuthNavbar/AuthNavbar';

import routes from '../../routes/dashboard';

import authStyles from '../../assets/jss/frontend/layouts/authStyle';

import login from '../../assets/img/login.jpeg';

import { connect } from 'react-redux';

class Auth extends React.Component {
    constructor(props){
        super(props);
        this.state = {
            redirect: false,
        }
    }
    componentDidMount() {
        document.body.style.overflow = "unset";
    }

    getRoutes = routes => {
        return routes.map((prop,key) => {
            if(prop.layout === '/auth') {
                return (
                    <Route 
                        path={prop.layout + prop.path}
                        component={prop.component}
                        key={key}
                    />
                );
            }
            else {
                return null;
            }
        });
    }
    getBgImage = () => {
        return login;
    }
    getActiveRoute = routes => {
        let activeRoute = "AUTH";
        for(let i=0;i < routes.length; i++) {
            if(window.location.href.indexOf(routes[i].layout + routes[i].path) !== -1) {
                return routes[i].name;
            }
        }
        return activeRoute;
    }

    render() {
        const { classes, ...rest } = this.props;
        // if(this.state.redirect) return (<Redirect from='/auth/login' to='/'/>)
        return (
            <div>
                <AuthNavbar brandText={this.getActiveRoute(routes)} {...rest}/>
                <div className={classes.wrapper} ref="wrapper">
                    <div
                        className={classes.fullPage}
                        style={{ backgroundImage: "url("+ this.getBgImage() +")"}}
                    >
                        <Switch>{this.getRoutes(routes)}</Switch>
                    </div>
                </div>
            </div>
        );
    }
}

Auth.propTypes = {
    classes: PropTypes.object.isRequired
};

const mapStateToProps = state => {
    return {
        authenticated: state.login.authenticated,
    }
}

export default withRouter(connect(mapStateToProps,null)(withStyles(authStyles)(Auth)));