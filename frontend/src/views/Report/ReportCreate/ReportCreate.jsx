import React from 'react';
import Axios from 'axios';
import {withStyles} from '@material-ui/core/styles';
import ChartistGraph from 'react-chartist';
import {connect} from 'react-redux';

import BarChart from '@material-ui/icons/BarChart';
import ShowChart from '@material-ui/icons/ShowChart';
import Sort from '@material-ui/icons/Sort';
import ViewList from '@material-ui/icons/ViewList';
import ViewModule from '@material-ui/icons/ViewModule';
import PieChart from '@material-ui/icons/PieChart';
import DonutLarge from '@material-ui/icons/DonutLarge';
import ScatterPlot from '@material-ui/icons/ScatterPlot';
import ZoomOutMap from '@material-ui/icons/ZoomOutMap';

import GridContainer from '../../../components/Grid/GridContainer';
import GridItem from '../../../components/Grid/GridItem';
import Card from '../../../components/Card/Card';
import CardHeader from '../../../components/Card/CardHeader';
import CardIcon from '../../../components/Card/CardIcon';
import CardBody from '../../../components/Card/CardBody';
import CardFooter from '../../../components/Card/CardFooter';
import ReportToolbar from "../../../components/ReportToolbar/ReportToolbar";
import Aux from '../../../hoc/aux/aux';
import Danger from '../../../components/Typography/Danger';
import FilterOptions from '../../../components/FilterOptions/FilterOptions';

import { handleDataLoad, handleDefaultDataLoad, handleClearReportData } from '../../../store/Actions/ActionCreator'

import {
    roundedLineChart,
    straightLinesChart,
    simpleBarChart,
    colouredLineChart,
    multipleBarsChart,
    colouredLinesChart,
    pieChart
  } from "variables/charts.jsx";

import reportCreateStyle from '../../../assets/jss/frontend/views/reportCreateStyle';

let resetFunc;

class ReportCreate extends React.Component{
    constructor(){
        super();
        this.state = {
            datasets : [],
            fields : [],
            reportTitle : '',
            reportType: '',
            reportDescription : '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : '',
            selectedDataset :  '',
            reportOptions : {},
            reportListeners : {},
            filterChecked : false,
            selectedOperation : '',
            selectedGroupBy : '',
            selectedMeasureOperation : 'LAST'
        };
        this.ref = React.createRef();
        // this.resetFunc.bind(this);
    };

    // resetFunc = () => {}

    componentDidMount(){
        this.getDatasets();
    }

    getDatasets = () => {
        Axios.get('http://127.0.0.1:8000/api/datasets/')
        .then(res => {
            this.setState({ datasets : [...res.data]})
        }); 
    };

    componentWillUnmount(){
        this.props.handleClearReportData();
    }

    handleDatasetChange = (e) => {
        console.log(e.currentTarget, typeof(e.target.value));
        e.persist();
        this.setState(prevState => {
            var i;
            let newFields = [];
            for(i=0; i < prevState.datasets.length; i++){
                console.log(e.target.value);
                if(prevState.datasets[i].dataset_id == e.target.value){
                    newFields = prevState.datasets[i].fields;
                    break;
                }
            }
            return { selectedDataset : e.target.value, fields : [...prevState.fields, ...newFields]}
        });
    };

    handleChange =  name => (e) => {
        console.log(e.currentTarget.value);
        this.setState({ [name] : e.currentTarget.value })
    }

    handleGraphChange = e => {
        const defaultData = this.getDefaultGraph(e.currentTarget.value);
        console.log(defaultData);
        this.setState({
            ...defaultData
        });
    }

    getDefaultGraph = name =>  {
        switch(name){
            case 'Bar':
                this.props.handleDefaultDataLoad(multipleBarsChart);
                return {
                    reportType : name,
                    icon : (<BarChart/>),
                    reportOptions : multipleBarsChart.options,
                    reportListeners : multipleBarsChart.animation
                }
            case "Line":
                this.props.handleDefaultDataLoad(colouredLinesChart);
                return {
                    reportType : name,
                    icon : (<ShowChart />),
                    reportOptions : colouredLinesChart.options,
                    reportListeners : colouredLinesChart.animation
                }
            default:
                return {}
        }
    }

    handleFieldChange  = (xField,yField) => {
        if(yField === null) {
            this.setState(prevState => {
                const newSelectedFields = [...prevState.selectedFields];
                newSelectedFields[0] = xField;
                return{
                selectedFields : newSelectedFields,
                selectedXField : xField
            }});
        }
        else {
            this.setState(prevState => {
                const newSelectedFields = [...prevState.selectedFields];
                newSelectedFields[1] = yField
                return {
                selectedFields : newSelectedFields,
                selectedYField : yField
            }});
        }
    };

    handleCancel = () => {
        this.props.handleClearReportData();
        this.setState({ fields : [],
            reportTitle : '',
            reportType: '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : '',
            selectedDataset :  '',
            selectedGroupBy : ''
        });
    }

    handleLoad = () => {
        const postData = {
                'type' : this.state.reportType,
                'dataset' : this.state.selectedDataset,
                'options' : {
                    'X_field' : this.state.selectedXField,
                    'Y_field' : this.state.selectedYField,
                    'group_by' : this.state.selectedGroupBy,
                    'measure_operation' : this.state.selectedMeasureOperation
                }
            }
        this.props.handleDataLoad(postData);
    }

    handleFilterToggle = () => {
        this.setState(prevState => ({ filterChecked : !prevState.filterChecked }));
    }

    handleFilterOptions = (state) => {
        this.setState(prevState => {
            const new_report_data = {
                ...prevState.report_data,
                labels : [...prevState.report_data.labels].slice(state.xRange[0],state.xRange[1]+1)
            };
            for(let i=0;i < new_report_data.series.length; i++){
                new_report_data.series[i] = [...new_report_data.series[i]].slice(state.yRange[0], state.yRange[1] +1)
            }
            return { report_data : new_report_data, selectedOperation : state.selectedOperation }
        })
    }

    handleSave = () => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/reports/',
            method: 'POST',
            data: JSON.stringify({
                'dataset_id' : this.state.selectedDataset,
                'data' : {
                    'report_type' : this.state.reportType,
                    'report_title' : this.state.reportTitle,
                    'report_description' : this.state.reportDescription,
                    'reported' : false,
                    'initial' : true
                }
            }),
            auth: {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : {
                'Content-Type' : 'application/json'
            }
        }
        Axios(postData)
        .then(res => this.props.history.push('/reports/list'))
    }

    handleGroupByChange = value => {
        this.setState({ selectedGroupBy : value });
    }

    handleMeasureOperation = op => {
        this.setState({ selectedMeasureOperation : op });
    }



    render(){
        let report_data = null;
        const {classes} = this.props;
        if(Object.keys(this.props.reportData).length !== 0 && this.props.reportData.constructor === Object){
            report_data = (<GridContainer>
                <GridItem xs={12} sm={12} md={6}>
                <Card>
                    <CardHeader color="success" icon>
                        <CardIcon color="success">
                            {this.state.icon}
                        </CardIcon>
                        <h4 className={classes.cardIconTitle}>
                            {this.state.reportTitle}
                        </h4>
                    </CardHeader>
                    <CardBody>
                        <ChartistGraph 
                            data={this.props.reportData}
                            type={this.state.reportType}
                            options={this.state.reportOptions}
                            listener={this.state.reportListeners}
                        />
                    </CardBody>
                    <CardFooter stats>
                        <div className={classes.stats}>
                        <Danger>
                            <ZoomOutMap />
                        </Danger>
                        <a href="#pablo" onClick={e => {
                            console.log(resetFunc);
                            resetFunc && resetFunc();
                            }}>
                            Zoom
                        </a>
                        </div>
                    </CardFooter>
                </Card>
                </GridItem>
                <GridItem xs={12} sm={12} md={6}>
                    <FilterOptions 
                        yLen={this.props.reportData.series[0].length}
                        xLen={this.props.reportData.labels.length}
                        filterChecked = {this.state.filterChecked}
                        handleFilterToggle={this.handleFilterToggle}
                        handleFilterOptions={this.handleFilterOptions}
                        handleSave={this.handleSave}
                    />
                </GridItem>
            </GridContainer>);
        }
        return (
            <Aux>
                <ReportToolbar
                    datasets = {this.state.datasets}
                    fields = {this.state.fields}
                    reportTitle = {this.state.reportTitle}
                    reportType = {this.state.reportType}
                    reportDescription = {this.state.reportDescription}
                    handleChange = {this.handleChange}
                    handleGraphChange = {this.handleGraphChange}
                    handleDatasetChange={this.handleDatasetChange}
                    handleFieldChange={this.handleFieldChange}
                    handleCancel={this.handleCancel}
                    handleLoad={this.handleLoad}
                    selectedYField = {this.state.selectedYField}
                    selectedDataset  ={this.state.selectedDataset}
                    selectedFields = {this.state.selectedFields}
                    selectedXField = {this.state.selectedXField}
                    selectedMeasureOperation = {this.state.selectedMeasureOperation}
                    selectedGroupBy = {this.state.selectedGroupBy}
                    handleGroupByChange = {this.handleGroupByChange }
                    handleMeasureOperation = {this.handleMeasureOperation}
                 />
                {report_data}

            </Aux>
        );
    }
}

const mapStateToProps = state => {
    return {
        reportData : state.report.reportData
    }
};

const mapDispatchToProps = dispatch => {
    return {
        handleDataLoad : data => dispatch(handleDataLoad(data)),
        handleDefaultDataLoad : data => dispatch(handleDefaultDataLoad(data)),
        handleClearReportData : () => dispatch(handleClearReportData())
    }
}

export default connect(mapStateToProps, mapDispatchToProps)(withStyles(reportCreateStyle)(ReportCreate));