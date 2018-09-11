import React from 'react';
import { connect } from 'react-redux';

import {login} from '../../store/Actions/ActionCreator';

class HomePage extends React.Component{
    componentDidMount(){

        const loginData = {
            email : "codemycompany@gmail.com",
            organization_id: "c479676e",
            password : "123456"
        };
        console.log(loginData);
        this.props.login(loginData);
    }
    render(){
        if(this.props.loginState.token !== ''){
            return (<div>login Success</div>)
        }
        return (<div>hi</div>);
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