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
import Graph from '../../../components/Graph/Graph';


import {login, handleDashCustomizeFetchData, clearDashCustomizeData} from '../../../store/Actions/ActionCreator';
import FixedPlugin from '../../../components/FixedPlugin/FixedPlugin';


class HomePage extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            tc : false,
            dashReportsdata : [],
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
        this.props.clearDashCustomizeData();
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

        // const loginData = {
        //     email : "shreyanshkitu.10@gmail.com",
        //     organization_id: "pragyaamtesting2",
        //     password : "Pragyaam@12345"
        // };
        // console.log(loginData);
        // this.props.login(loginData);

        const postData = {
            method : 'GET',
            url : `${process.env.REACT_APP_API_URL}/reports/`,
            headers : {
                'Authorization' : `Token ${this.props.auth_token}`
            }
        };
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

            dashReportsdata = res.data.filter(x => {
                if(!x.data.reported) return false;
                return true;
            }).map(report => {
                
                let checkReport = { ...report };

                
                if(report.data.reported && report.data.initial){
                    this.props.handleDashCustomizeFetchData(report.data, report.report_id);
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
                    this.props.handleDashCustomizeFetchData(report.data, report.report_id);
                    checkReport = {
                        ...report
                    }
                }

                return checkReport;

            });}


            return { dashReportsdata : [...prevState.dashReportsdata, ...dashReportsdata ]};
        }))
    }

    componentDidUpdate(prevProps){
        if(this.props.loginState.token !== '' && this.props.loginState.token !== prevProps.loginState.token){
            this.showNotification('tc');
        }
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
                    enableResizing = {false}
                index={dashReport.report_id}
                >

                    <Graph 
                        index={dashReport.report_id}
                        data = {report_data.data}
                        type = {dashReport.data.report_type}
                        options = {dashReport.data.report_options.reportOptions}
                        listeners = {dashReport.data.report_options.reportListeners}
                        width = {dashReport.data.pos.width}
                        height = {dashReport.data.pos.height}
                        />
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
        </div>
        );
    }
}

const mapStateToProps = state => {
    return {
        loginState : state.login,
        dashReportCustomize : state.dashboard.dashReportCustomize,
        auth_token : state.login.auth_token,
    }
}

const mapDispatchToProps = dispatch => {
    return {
        login : loginData => dispatch(login(loginData)),
        handleDashCustomizeFetchData : (data,id) => dispatch(handleDashCustomizeFetchData(data, id)),
        clearDashCustomizeData : () => dispatch(clearDashCustomizeData())
    }
}

export default connect(mapStateToProps,mapDispatchToProps)(HomePage); 