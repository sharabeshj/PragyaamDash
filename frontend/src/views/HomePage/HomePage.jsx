import React from 'react';
import { connect } from 'react-redux';

import { withStyles } from '@material-ui/core/styles';
import AddAlert from '@material-ui/icons/AddAlert';

import GridContainer from '../../components/Grid/GridContainer';
import GridItem from '../../components/Grid/GridItem';
import CustomButton from '../../components/CustomButtons/Button';
import Snackbar from '../../components/Snackbar/Snackbar';

import homepageStyle from '../../assets/jss/frontend/views/homepageStyle';

import {login} from '../../store/Actions/ActionCreator';
import Axios from 'axios';

class HomePage extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            tc : false,
            dashReportsdata : []
        };
    }

    componentWillUnmount(){
        let id = window.setTimeout(null, 0);
        while(id --) {
            window.clearInterval(id);
        }
    }

    showNotification(place){
        if(!this.state.tc){
        
            this.setState({ tc : true });
            setTimeout(
                function(){
                    // console.log('hello');
                    this.setState({ tc : false });
                }.bind(this),
                4000
            );
        }
    }

    componentDidMount(){

        const loginData = {
            email : "codemycompany@gmail.com",
            organization_id: "c479676e",
            password : "123456"
        };
        console.log(loginData);
        this.props.login(loginData);

        const postData = {
            method : 'GET',
            url : 'http://127.0.0.1:8000/api/reports/',
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            }
        };

        Axios(postData)
        .then(res => this.setState(() => {
            let dashReportsdata = [];
            dashReportsdata = res.data.map(report => {
                if(report.reported && initial){
                    return {
                        ...report,
                    }
                }
            })
        }))
    }

    componentDidUpdate(prevProps){
        if(this.props.loginState.token !== '' && this.props.loginState.token !== prevProps.loginState.token){
            this.showNotification('tc');
        }
    }

    render(){
        

        return (<div>
            <Snackbar 
                place="tc"
                color="info"
                icon = {AddAlert}
                message="Login Sucess! Welcome to Pragyaam Dash"
                open={this.state.tc}
                closeNotification = { () => this.setState({ tc : false })}
                close
            />
        </div>);
    }
}

const mapStateToProps = state => {
    return {
        loginState : state.login
    }
}

const mapDispatchToProps = dispatch => {
    return {
        login : loginData => dispatch(login(loginData))
    }
}

export default connect(mapStateToProps,mapDispatchToProps)(HomePage);