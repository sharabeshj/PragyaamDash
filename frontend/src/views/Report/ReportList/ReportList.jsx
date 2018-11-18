import React from 'react';
import Axios from 'axios';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import {Link} from 'react-router-dom';
import ChartistGraph from 'react-chartist';

import Button from '@material-ui/core/Button';
import CssBaseline from '@material-ui/core/CssBaseline';
import Grid from '@material-ui/core/Grid';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';
import Add from '@material-ui/icons/Add';
import Refresh from '@material-ui/icons/Refresh';
import Edit from '@material-ui/icons/Edit';
import AccessTime from '@material-ui/icons/AccessTime';

import CustomButton from '../../../components/CustomButtons/Button';
import GridContainer from '../../../components/Grid/GridContainer';
import GridItem from '../../../components/Grid/GridItem';
import Card from '../../../components/Card/Card';
import CardHeader from '../../../components/Card/CardHeader';
import CardBody from '../../../components/Card/CardBody';
import CardFooter from '../../../components/Card/CardFooter';
import aux from '../../../hoc/aux/aux';

import reportListStyles from '../../../assets/jss/frontend/views/ReportList';
import { Tooltip } from '@material-ui/core';

import {
    roundedLineChart,
    straightLinesChart,
    simpleBarChart,
    colouredLineChart,
    multipleBarsChart,
    multipleBarsChartReport,
    colouredLinesChart,
    colouredLinesChartReport,
    pieChart
  } from "variables/charts.jsx";


class ReportList extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            reportDataList : []
        };
    }

    componentDidMount(){
        const data = {
            url : 'http://127.0.0.1:8000/api/reports/',
            method : 'GET',
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            }
        };
        Axios(data)
        .then(res => {
            this.setState({ reportDataList : res.data });
            // this.loadReportdata();
        })
        .catch(e => console.error(e));
    }

    moveToDashbaord = (report) => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/reports/',
            method : 'PUT',
            data : JSON.stringify({
                ...report,
                data : {
                    ...report.data,
                    reported : true
                }
            }),
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
        .then(res => this.props.history.push('/'))
    }

    // loadReportdata = () => {
    //     this.state.reportDataList.forEach(report => {
    //         window.mpld3.draw_figure(String(this.state.reportDataList.indexOf(report)),report.data)
    //     });
    // }

    render(){
        const { classes } = this.props;
        const colorChoices =  ['success','warning','danger','info'];
        
        return (
                <aux>
                <div className={classes.heroUnit}>
                            <div className={classes.heroContent}>
                                <Typography component="h1" variant="h2" align="center" color = "textPrimary" gutterBottom>
                                    Report Customization
                                </Typography>
                                <Typography variant="h6" align="center" color="textSecondary" paragraph> 
                                    Collection of reports generated by various users - Customizable and save to dashboard 
                                </Typography>
                                <div className={classes.heroButtons}>
                                    <Grid container spacing={16} justify="center">
                                        <Grid item>
                                        <Link to='/reports/create'>
                                        <CustomButton size = 'md' color="primary">
                                                Create Report<Add/>
                                            </CustomButton>
                                        </Link>
                                            
                                        </Grid>
                                        <Grid item>
                                            <Button variant="outlined" color="success">
                                                <Link to="/dashboard">View dashboard</Link>
                                            </Button>
                                        </Grid>
                                    </Grid>
                                </div>
                            </div>
                        </div>
                        {/* <div className={classNames(classes.layout, classes.cardGrid)}>
                            <Grid container spacing={40}>
                                {this.state.reportDataList.map(report => (
                                    <Grid item key={report.data} sm={6} md={4} lg={3}>
                                        <Card className={classes.card}>
                                            <CardMedia 
                                                className={classes.cardMedia}
                                                id={String(this.state.reportDataList.indexOf(report))}
                                            />
                                            <CardContent className={classes.card}>
                                                <Typography gutterBottom variant="h5" component="h2">
                                                    {report.title}
                                                </Typography>
                                                <Typography>
                                                    {report.description}
                                                </Typography>
                                            </CardContent>
                                            <CardActions>
                                                <Button size="small" color="success">
                                                    Add
                                                </Button>
                                                <Button size="small" color="success">
                                                    Edit
                                                </Button>
                                            </CardActions>
                                        </Card>
                                    </Grid>
                                ))}
                            </Grid>
                        </div> */}

                    <h3>Reports</h3>
                    <br />
                    <GridContainer>
                        {this.state.reportDataList.map((report) => {

                            let reportOptions = {}, reportListeners = {}, reportResponsive={};

                            switch(report.data.report_type){
                                case 'Bar':
                                    reportOptions=multipleBarsChartReport.options;
                                    reportListeners = multipleBarsChartReport.animation;
                                    reportResponsive = multipleBarsChartReport.responsiveOptions;
                                    break;
                                case 'Line':
                                    reportOptions = colouredLinesChartReport.options;
                                    reportListeners = colouredLinesChartReport.animation;
                                default:
                                    break;
                            }
                            
                            const color = colorChoices[Math.floor(Math.random()*colorChoices.length)];

                            return (
                            <GridItem key = {report.report_id} xs={12} sm={12} md={4}>
                                <Card chart className={classes.cardHover}>
                                    <CardHeader 
                                    color = {color}
                                    className={classes.cardHeaderHover}>
                                        <ChartistGraph 
                                            className="ct-chart-white-colors"
                                            data={report.data.report_data}
                                            type={report.data.report_type}
                                            options={reportOptions}
                                            // responsiveOptions = {reportResponsive}
                                            listener={reportListeners}
                                        /> 
                                    </CardHeader>
                                    <CardBody>
                                        <div className={classes.cardHoverUnder}>
                                            <Tooltip
                                                id="tooltip-top"
                                                title="Refresh"
                                                placement="bottom"
                                                classes={{ tooltip: classes.tooltip }}
                                            >
                                                <CustomButton simple color="info" justIcon>
                                                    <Refresh className={classes.underChartIcons} />
                                                </CustomButton>
                                            </Tooltip>
                                            <Tooltip
                                                id="tooltip-top"
                                                title="Edit"
                                                placement="bottom"
                                                classes={{ tooltip : classes.tooltip }}
                                            >
                                                <CustomButton color="transparent" simple justIcon>
                                                    <Edit className={classes.underChartIcons}/>
                                                </CustomButton>
                                            </Tooltip>
                                            </div>
                                            <h4 className={classes.cardTitle}>{report.data.report_title}</h4>
                                            <p className={classes.cardCategory}>
                                                {report.data.report_description}
                                            </p>
                                        
                                    </CardBody>
                                    <CardFooter chart>
                                        <div className={classes.stats}>
                                            <AccessTime /> Updated 2 days ago
                                            <CustomButton size="sm" color = {color} onClick={() => this.moveToDashbaord(report)} disabled={true ? report.data.reported : false}>
                                                {report.data.reported?"Reported":"Report To Dash"}
                                            </CustomButton>
                                        </div>
                                    </CardFooter>
                                </Card>
                            </GridItem>
                        );
                    })}
                    </GridContainer>
                </aux>
                    
        );
    }
}

ReportList.propTypes = {
    classes : PropTypes.object.isRequired,
};

export default withStyles(reportListStyles)(ReportList);