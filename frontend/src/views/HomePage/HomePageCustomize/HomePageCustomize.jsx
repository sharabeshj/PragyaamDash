import React from 'react';
import { connect } from 'react-redux';
import Axios from 'axios';
import { Rnd } from 'react-rnd';
import update from 'react-addons-update';
import ChartistGraph from 'react-chartist';


import { withStyles } from '@material-ui/core/styles';
import AddAlert from '@material-ui/icons/AddAlert';

import GridContainer from '../../../components/Grid/GridContainer';
import GridItem from '../../../components/Grid/GridItem';
import CustomButton from '../../../components/CustomButtons/Button';
import Snackbar from '../../../components/Snackbar/Snackbar';
import Card from '../../../components/Card/Card';
import CardBody from '../../../components/Card/CardBody';


import {login, handleFetchData} from '../../../store/Actions/ActionCreator';


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

            if(res.data.length > 0){
                const parsedData = res.data.map(report => ({ 
                    'id' : report.report_id , 
                    'reportOptions' : this.parseFunctionInJson(JSON.stringify(report.data.report_options.reportOptions)), 
                    'reportListeners' : this.parseFunctionInJson(JSON.stringify(report.data.report_options.reportListeners) )
                }));
                console.log("here");
                console.log(parsedData);

            dashReportsdata = res.data.filter(x => {
                if(!x.data.reported) return false;
                return true;
            }).map(report => {
                
                let checkReport = { ...report };

                for(let i =0 ; i < parsedData.length ; i++){
                    if(parsedData[i].id === report.report_id){
                        checkReport = {
                            ...report,
                            data : {
                                ...report.data,
                                report_options : {
                                    ...report.data.report_options,
                                    reportOptions : parsedData[i].reportOptions,
                                    reportListeners : parsedData[i].reportListeners
                                }
                            }
                        }
                    }
                }
                
                if(report.data.reported && report.data.initial){
                    this.props.handleFetchData(report.data, report.report_id);
                    checkReport =  {
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
                else if(report.data.reported && !report.data.initial){
                    this.props.handleFetchData(report.data, report.report_id);
                    checkReport = {
                        ...report
                    }
                }

                return checkReport;

            });}


            this.setState({ dashReportsdata : [...prevState.dashReportsdata, ...dashReportsdata ]});
        }))
    }

    componentDidUpdate(prevProps){
        if(this.props.loginState.token !== '' && this.props.loginState.token !== prevProps.loginState.token){
            this.showNotification('tc');
        }
    }

    parseFunctionInJson = json => {

        return JSON.parse(json, (key,value) => {
            if(value.constructor === Array){
                let newValue = [];
                for(let i =0; i < value.length; i++){
                    console.log(value[i].replace(/\/\/.*$|\/\*[\s\S]*?\*\//mg, '').replace(/\s+/g, ' ').trim());
                    if(this.checFunctionInJson(value[i].replace(/\/\/.*$|\/\*[\s\S]*?\*\//mg, '').replace(/\s+/g, ' ').trim())){
                        console.log("yes");
                        newValue.push(this.makeFunctionFromJson(value[i].replace(/\/\/.*$|\/\*[\s\S]*?\*\//mg, '').replace(/\s+/g, ' ').trim()));
                    }
                    else newValue.push(value[i]);
                }
                return newValue
            }
            else if(value.constructor === Object){
                let newObject = {};
                Object.keys(value).forEach(k => {
                    if(this.checFunctionInJson(value[k]))
                    newObject = {
                        ...value,
                        k : this.makeFunctionFromJson(value[k])
                    };
                    else newObject = { ...value };
                });
                return newObject;
            }
            else if(this.checFunctionInJson(value)){
                return this.makeFunctionFromJson(value);
            }
            else {
                return value;
            }
        });
    }

    checFunctionInJson = value => {
        return /^function.*?\(.*?\)\s*\{.*\}$/.test(value);
    }
    
    makeFunctionFromJson = value => {
        value = value.replace (/(^")|("$)/g, '')
        eval(value);
    }

    render(){
        let dashReportsdata = null;
        const style = {
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "solid 1px #ddd",
            background: "#fff",
            borderRadius : "5px"
          };

        if(this.state.dashReportsdata.length > 0 && this.props.dashReportCustomize.length === this.state.dashReportsdata.length){
            console.log(this.state.dashReportsdata);
            dashReportsdata = this.state.dashReportsdata.map( (dashReport,index) => {
                const report_data = this.props.dashReportCustomize.find(x => (x.id === dashReport.report_id));
                console.log(dashReport.report_id);
                return (<Rnd
                    style={style}
                    key = {index}
                    size = {{ width : dashReport.data.pos.width, height : dashReport.data.pos.height }}
                    position = {{ x : dashReport.data.pos.x, y : dashReport.data.pos.y }}
                    onDragStop = {(e,d) => {
                        if( typeof e.target.attributes['index'] !== "undefined"){
                        console.log(e.target.attributes);
                        for(let i = 0; i < this.state.dashReportsdata.length; i++){
                            if(this.state.dashReportsdata[i].report_id == e.target.attributes['index'].value){
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
                                    this.setState({ dashReportsdata : newDashReportsdata});
                                }
                               
                         
                            }
                        }
                    }
                    }}
                onResize = {(e, direction, ref, delta, position) => {
                    console.log(ref.getAttribute('index'));
                    for(let i = 0; i < this.state.dashReportsdata.length; i++){
                        if(this.state.dashReportsdata[i].report_id == ref.getAttribute('index')){
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
                            };
                            this.setState({ dashReportsdata : newDashReportsdata });
                        }
                    }
                }}
                index={dashReport.report_id}
                >
                        <div style= {{ width : `${dashReport.data.pos.width}`}}>
                            <ChartistGraph 
                            index={dashReport.report_id}
                                data = {report_data.data}
                                type = {dashReport.data.report_type}
                                options = {dashReport.data.report_options.reportOptions}
                                listeners = {dashReport.data.report_options.reportListeners}
                            />
                        </div>
                </Rnd>);
            })
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
        loginState : state.login,
        dashReportCustomize : state.dashboard.dashReportCustomize
    }
}

const mapDispatchToProps = dispatch => {
    return {
        login : loginData => dispatch(login(loginData)),
        handleFetchData : (data,id) => dispatch(handleFetchData(data, id))
    }
}

export default connect(mapStateToProps,mapDispatchToProps)(HomePage); 