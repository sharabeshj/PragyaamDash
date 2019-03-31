import React from 'react';
import cx from 'classnames';
import PropTypes from 'prop-types';

import withStyles from '@material-ui/core/styles/withStyles';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import Hidden from '@material-ui/core/Hidden';

import Button from '../CustomButtons/Button';

import authNavbarStyle from '../../assets/jss/frontend/components/authNavbarStyle';

class AuthNavbar extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            open: false
        };
    }
    handleDrawerToggle = () => {
        this.setState({ open: !this.state.open });
    };

    componentDidUpdate(e) {
        if (e.history.location.pathname !== e.location.pathname) {
            this.setState({ open: false });
          }
    }
    render() {
        const { classes, color, brandText } = this.props;
        const appBarClasses = cx({
        [" " + classes[color]]: color
        });
        return (
        <AppBar position="static" className={classes.appBar + appBarClasses}>
            <Toolbar className={classes.container}>
            <Hidden smDown>
                <div className={classes.flex}>
                <Button href="#" className={classes.title} color="transparent">
                    {brandText}
                </Button>
                </div>
            </Hidden>
            <Hidden mdUp>
                <div className={classes.flex}>
                <Button href="#" className={classes.title} color="transparent">
                    LOGIN
                </Button>
                </div>
            </Hidden>
            </Toolbar>
        </AppBar>
        );
    }
}

AuthNavbar.propTypes = {
    classes: PropTypes.object.isRequired,
    color: PropTypes.oneOf(["primary", "info", "success", "warning", "danger"]),
    brandText: PropTypes.string
};

export default withStyles(authNavbarStyle)(AuthNavbar);