import React from 'react';
import {connect} from 'react-redux';
import { withRouter } from 'react-router-dom';

import withStyles from '@material-ui/core/styles/withStyles';
import InputAdornment from '@material-ui/core/InputAdornment';
import Icon from '@material-ui/core/Icon';

import Face from '@material-ui/icons/Face';
import Email from '@material-ui/icons/Email';

import GridContainer from '../../components/Grid/GridContainer';
import GridItem from '../../components/Grid/GridItem';
import CustomInput from '../../components/CustomInput/CustomInput';
import Button from '../../components/CustomButtons/Button';
import Card from '../../components/Card/Card';
import CardBody from '../../components/Card/CardBody';
import CardHeader from '../../components/Card/CardHeader';
import CardFooter from '../../components/Card/CardFooter';

import loginPageStyle from '../../assets/jss/frontend/views/loginPageStyle';

import { login } from '../../store/Actions/ActionCreator';

class LoginPage extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            cardAnimation: "cardHidden",
            organisation_id: '',
            user_email: '',
            password: ''
        };
    }
    componentDidMount() {
        this.timeOutFunction = setTimeout(
            function() {
                this.setState({ cardAnimation: "" });
            }.bind(this),
            700
        );
    }
    static getDerivedStateFromProps(props,state) {
        if(props.authenticated === true) {
          props.history.push('/home')
        }
      }
    componentWillUnmount() {
        clearTimeout(this.timeOutFunction);
        this.timeOutFunction = null;
    }

    handleChange = (e) => {
        this.setState({ [e.target.id] : e.target.value });
    }

    render() {
        const { classes,login } = this.props;
        return (
            <div className={classes.container}>
                <GridContainer justify="center">
                    <GridItem xs={12} sm={6} md={4}>
                        <form>
                            <Card login className={classes[this.state.cardAnimation]}>
                                <CardHeader
                                    className={`${classes.CardHeader} ${classes.textCenter}`}
                                    color="rose"
                                >
                                    <h4 className={classes.cardTitle}>Log In</h4>
                                </CardHeader>
                                <CardBody>
                                    <CustomInput
                                        onChange={this.handleChange}
                                        labelText="Organistion Id.."
                                        id="organisation_id"
                                        formControlProps={{
                                            fullWidth: true
                                        }}
                                        inputProps={{
                                            endAdornment: (
                                                <InputAdornment position="end">
                                                    <Face className={classes.inputAdornmentIcon}/>
                                                </InputAdornment>
                                            )
                                        }}
                                    />
                                    <CustomInput
                                        onChange={this.handleChange}
                                        labelText="Email.."
                                        id="user_email"
                                        formControlProps={{
                                            fullWidth: true
                                        }}
                                        inputProps={{
                                            endAdornment: (
                                                <InputAdornment position="end">
                                                    <Email className={classes.inputAdornmentIcon}/>
                                                </InputAdornment>
                                            )
                                        }}
                                    />
                                    <CustomInput
                                        onChange={this.handleChange}
                                        labelText="Password"
                                        id="password"
                                        formControlProps={{
                                        fullWidth: true
                                        }}
                                        inputProps={{
                                        endAdornment: (
                                            <InputAdornment position="end">
                                            <Icon className={classes.inputAdornmentIcon}>
                                                lock_outline
                                            </Icon>
                                            </InputAdornment>
                                        )
                                        }}
                                    />
                                </CardBody>
                                <CardFooter className={classes.justifyContentCenter}>
                                    <Button color="rose" simple size="lg" block onClick={() => login(this.state)}>
                                        Let's Go
                                    </Button>
                                </CardFooter>
                            </Card>
                        </form>
                    </GridItem>
                </GridContainer>
            </div>
        );
    }
}

const mapStateToProps = state => {
    return {
        authenticated: state.login.authenticated,
    }
}

const mapDispatchToProps = (dispatch) => ({
    login: (loginData) => dispatch(login(loginData)),
});

export default withRouter(connect(mapStateToProps, mapDispatchToProps)(withStyles(loginPageStyle)(LoginPage)));