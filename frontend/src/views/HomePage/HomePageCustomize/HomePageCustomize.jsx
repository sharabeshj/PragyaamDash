import React from 'react';
import { connect } from 'react-redux';
import Axios from 'axios';
import { Rnd } from 'react-rnd';
import update from 'react-addons-update';

import { withStyles } from '@material-ui/core/styles';
import AddAlert from '@material-ui/icons/AddAlert';

import GridContainer from '../../../components/Grid/GridContainer';
import GridItem from '../../../components/Grid/GridItem';
import CustomButton from '../../../components/CustomButtons/Button';
import Snackbar from '../../../components/Snackbar/Snackbar';


import {login} from '../../../store/Actions/ActionCreator';


class HomePage extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            tc : false,
            dashReportsdata : []
        };
    }

    _ismounted = false;

    componentWillUnmount(){
        let id = window.setTimeout(null, 0);
        while(id --) {
            window.clearInterval(id);
        }
        console.log('unmounted');
        this._ismounted = false;
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
        this._ismounted = true;

        const loginData = {
            email : "testing@gmail.com",
            organization_id: "testorg",
            password : "Testing123!"
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
        console.log('component did mount');
        Axios(postData)
        .then(res => this.setState((prevState) => {
            let x_available=0,y_available=0,dashReportsdata = [];
            for(let i=0; i < res.data.length; i++){
                if(res.data[i].reported && !res.data[i].initial){
                    x_available = x_available + res.data[i].data.pos.x + res.data[i].data.pos.width;
                    if(x_available >= window.screen.width){
                        x_available = 0;
                        y_available = y_available + res.data[i].data.pos.y + res.data[i].data.pos.height
                    }
                }
            }
            console.log(x_available, y_available);

            dashReportsdata = res.data.map(report => {  

                if(report.data.reported && report.data.initial){

                    return {
                        ...report,
                        data : {
                            ...report.data,
                            pos : {
                                x : x_available,
                                y : y_available,
                                width: 400,
                                height : 300
                            }
                        }
                    }
                }
                else if(report.data.reported){
                    return {
                        ...report
                    }
                }
                else {
                    return {
                        ...report
                    }
                }
            });
            
            this.setState({ dashReportsdata : [...prevState.dashReportsdata, ...dashReportsdata ]});
        }))
    }

    componentDidUpdate(prevProps){
        if(this.props.loginState.token !== '' && this.props.loginState.token !== prevProps.loginState.token){
            this.showNotification('tc');
        }
    }

    render(){
        let dashReportsdata = null;
        if(this.state.dashReportsdata.length > 0){
            console.log(this.state.dashReportsdata);
            dashReportsdata = this.state.dashReportsdata.map( (dashReport,index) => (
                <Rnd
                    key = {index}
                    index={index}
                    size = {{ width : dashReport.data.pos.width, height : dashReport.data.pos.height }}
                    position = {{ x : dashReport.data.pos.x, y : dashReport.data.pos.y }}
                    onDragStop = {(e,d) => {
                        console.log(e.target.attributes['index'].value);
                        for(let i = 0; i < this.state.dashReportsdata.length; i++){
                            if(i == e.target.attributes['index'].value){
                                console.log(this.state.dashReportsdata[0]);
                                const newDashReportsdata = [
                                    ...this.state.dashReportsdata
                                ];
                                newDashReportsdata[i] = { 
                                    ...newDashReportsdata[i], 
                                    data : { 
                                        ...newDashReportsdata[i].data,
                                        initial : false, 
                                        pos : {
                                            ...newDashReportsdata[i].data.pos,
                                            x : d.x,
                                            y : d.y
                                        }
                                    }
                                }
                                console.log(newDashReportsdata,this.state.dashReportsdata);
                                if(this._ismounted){
                                    console.log('here');    
                                    this.setState({ dashReportsdata : newDashReportsdata});
                                }
                               
                         
                            }
                        }
                    }}
                onResizeStop = {(e, direction, ref, delta, position) => {
                    console.log(ref.getAttribute('index'));
                    for(let i = 0; i < this.state.dashReportsdata.length; i++){
                        if(i == ref.getAttribute('index')){
                            const newDashReportsdata = [
                                ...this.state.dashReportsdata
                            ];
                            newDashReportsdata[i] = { 
                                ...newDashReportsdata[i], 
                                data : {
                                    ...this.state.dashReportsdata[i].data,
                                    pos : {
                                        ...this.state.dashReportsdata[i].data.pos,
                                        width : ref.style.width,
                                        height : ref.style.height
                                    }
                                }
                            }
                        }
                    }
                }}
                >
                    hi
                </Rnd>
            ))
        }

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
            {dashReportsdata}
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

export default connect(mapStateToProps,mapDispatchToProps)(HomePage); // const loginData = {
    //     email : "codemycompany@gmail.com",
    //     organization_id: "c479676e",
    //     password : "123456"
    // };
    // console.log(loginData);
    // this.props.login(loginData);