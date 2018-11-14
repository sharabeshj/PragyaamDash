import React from 'react';
import Axios from 'axios';
import {withStyles} from '@material-ui/core/styles';
import ChartistGraph from 'react-chartist';

import GridContainer from '../../../components/Grid/GridContainer';
import GridItem from '../../../components/Grid/GridItem';
import Card from '../../../components/Card/Card';
import CardHeader from '../../../components/Card/CardHeader';
import CardIcon from '../../../components/Card/CardIcon';
import CardBody from '../../../components/Card/CardBody';
import CardFooter from '../../../components/Card/CardFooter';
import ReportToolbar from "../../../components/ReportToolbar/ReportToolbar";
import Aux from '../../../hoc/aux/aux';

import reportCreateStyle from '../../../assets/jss/frontend/views/reportCreateStyle';

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
            report_data : {}
        };
        this.ref = React.createRef();
    };

    componentDidMount(){
        this.getDatasets();
    }

    getDatasets = () => {
        Axios.get('http://127.0.0.1:8000/api/datasets/')
        .then(res => {
            this.setState({ datasets : [...res.data]})
        }); 
    };

    handleDatasetChange = (e) => {
        console.log(e.currentTarget, typeof(e.target.value));
        e.persist();
        this.setState(prevState => {
            var i;
            let newFields = [];
            for(i=0; i < prevState.datasets.length; i++){
                console.log(e.target.value);
                if(prevState.datasets[i].name == e.target.value){
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

    handleFieldChange  = (xField,yField) => {
        if(yField === null) {
            this.setState(prevState => ({
                selectedFields : [...prevState.selectedFields,xField],
                selectedXField : xField
            }));
        }
        else {
            this.setState(prevState => {
                if(prevState.selectedYField.indexOf(yField) === -1){
                    return {
                        selectedFields : [...prevState.selectedFields,yField],
                        selectedYField : [...prevState.selectedYField,yField]
                    }
                }
                else {
                    return {
                        selectedFields : [...prevState.selectedFields],
                        selectedYField : [...prevState.selectedYField]
                    }
                }
            });
        }
    };

    handleCancel = () => {
        this.setState({ fields : [],
            reportTitle : '',
            reportType: '',
            selectedFields : [],
            selectedXField : '',
            selectedYField : [],
            selectedDataset :  ''});
    }

    handleSave = () => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/report_generate/',
            method : 'POST',
            data : JSON.stringify({
                'type' : this.state.reportType,
                'dataset' : this.state.selectedDataset,
                'report_title' : this.state.reportTitle,
                'report_description' : this.state.reportDescription,
                'options' : {
                    'X_field' : this.state.selectedXField,
                    'Y_field' : this.state.selectedYField
                }
            }),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => this.setState((prevState) => {
                const data = res.data.data;
                // const new_data = data.slice(1,-1);
                return { report_data : {...data} };
            }))
            .catch(err => console.error(err));
    }

    render(){
        let report_data = null;
        const {classes} = this.props;
        if(Object.keys(this.state.report_data).length !== 0 && this.state.report_data.constructor === Object){
            report_data = (<GridContainer xs={12} sm={12} md={6}>
                <Card>
                    <CardHeader color="success" icon>
                        <CardIcon color="success">
                            {() => {
                                switch(this.state.reportType){
                                    case 'hor_bar':
                                        return (<Sort />);
                                    case 'line_graph':
                                        return (<ShowChart />);
                                    case 'bar':
                                        return (<BarChart />);
                                    case 'stacked_hor_bar':
                                        return (<ViewList />);
                                    case 'stacked_bar_graph':
                                        return (<ViewModule />);
                                    case 'pie_graph':
                                        return (<PieChart />);
                                    case 'donut_graph':
                                        return (<DonutLarge />);
                                    case 'scatter_graph':
                                        return (<ScatterPlot />);
                                }
                            }}
                        </CardIcon>
                        <h4 className={classes.cardIconTitle}>
                            {this.state.reportTitle}
                        </h4>
                    </CardHeader>
                    <CardBody>
                        <ChartistGraph 
                            data={this.state.report_data}
                            type={this.state.reportType}
                            options={this.state.reportOptions}
                            listener={this.state.reportAnimation}
                        />
                    </CardBody>
                </Card>
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
                    handleDatasetChange={this.handleDatasetChange}
                    handleFieldChange={this.handleFieldChange}
                    handleCancel={this.handleCancel}
                    handleSave={this.handleSave}
                    selectedYField = {this.state.selectedYField}
                    selectedDataset  ={this.state.selectedDataset}
                    selectedFields = {this.state.selectedFields}
                    selectedXField = {this.state.selectedXField}
                    selectedYField = {this.state.selectedYField}
                 />

                {report_data}

            </Aux>
        );
    }
}

export default withStyles(reportCreateStyle)(ReportCreate);