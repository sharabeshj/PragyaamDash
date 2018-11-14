import React from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';
import {Link} from 'react-router-dom';

import { withStyles } from '@material-ui/core/styles';
import Typography from '@material-ui/core/Typography';
import AccessTime from '@material-ui/icons/AccessTime';
import Add from '@material-ui/icons/Add';

import GridItem from '../../../components/Grid/GridItem';
import GridContainer from '../../../components/Grid/GridContainer';
import Card from '../../../components/Card/Card';
import CardBody from '../../../components/Card/CardBody';
import CardHeader from '../../../components/Card/CardHeader';
import CardFooter from '../../../components/Card/CardFooter';
import CustomButton from '../../../components/CustomButtons/Button';
import TableModal from '../../../components/TableModal/TableModal';

import datasetListStyle from '../../../assets/jss/frontend/views/datasetList';

class DatasetList extends React.Component{
    constructor(props){
        super(props);
        this.state = {
            datasets : [],
            modalOpen : false,
            tableData : [],
            name : ''
        }
    }
    componentDidMount(){
        this.getDatasets();
    }

    getDatasets = () => {
        axios.get('http://127.0.0.1:8000/api/datasets')
            .then(res => this.setState({ datasets : res.data }))
            .catch( e => console.error(e));
    }

    handleClose = () => this.setState({ modalOpen : false,tableData : [] });

    handleView = (name) => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/dataset_detail/',
            method : 'POST',
            data : JSON.stringify({
                name : name,
                view_mode : 'view'
            }),
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : {
                'Content-Type' : 'application/json'
            }
        }
        axios(postData)
            .then(res => this.setState({ modalOpen : true,tableData : res.data,name : name }))
            .catch(e => console.error(e));
    }

    handleAdd = (name) => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/dataset_detail/',
            method : 'POST',
            data : JSON.stringify({
                name : name,
                view_mode : 'add'
            }),
            auth : {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : {
                'Content-Type' : 'application/json'
            }
        }
        axios(postData)
            .then(res => this.setState({ modalOpen : true,tableData : res.data,name : name }))
            .catch(e => console.error(e));
    }
    render(){
        const { classes } = this.props;
        let datasets = null;
        const colorChoices =  ['success','warning','danger','info'];
        if(this.state.datasets !== []){
            datasets = this.state.datasets.map((dataset,index) => {
                const color = colorChoices[Math.floor(Math.random()*colorChoices.length)];
                return (
                        <GridItem key = {index} xs = {12} sm = {6} md = {4} lg = {4}>
                            <Card>
                                <CardHeader color = {color} >
                                    <h5 className = {classes.cardTitleWhite}>{dataset.name}</h5>
                                </CardHeader>
                                <CardBody>
                                    <div className = {classes.cardBody}>
                                         <Typography variant = "subheading">
                                            {`Fields - ${dataset.fields.length}`}
                                         </Typography>
                                         <CustomButton name = {dataset.name} color = {color} size = "sm" onClick = {() => this.handleView(dataset.name)}>
                                            View
                                         </CustomButton>
                                         <CustomButton name = {dataset.name} simple color = "success" size = "sm" onClick = {() => this.handleAdd(dataset.name)}>
                                            Add
                                         </CustomButton>
                                    </div>
                                </CardBody>
                                <CardFooter chart>
                                    <div className = {classes.stats}>
                                        <AccessTime />Updated 4 minutes ago
                                    </div>
                                    <div className = {classes.stats} >
                                        {`OWNER: ${dataset.profile}`}
                                    </div>   
                                </CardFooter>
                            </Card>
                        </GridItem>
            )});
            
        }
        return (
            <div>
                <div>
                    <Typography variant = 'Title' align = "center">
                        DATASETS
                    </Typography>

                    <CustomButton color = "success">
                        Create Dataset <Add />
                    </CustomButton>
                </div>
                <GridContainer>
                    {datasets}
                </GridContainer>
  
                {(this.state.tableData.length > 0 && this.state.modalOpen)  ? (<TableModal 
                                            title = {this.state.name}
                                            tableData = {this.state.tableData.map(data => {
                                                let dataArray = []
                                                Object.entries(data).forEach(
                                                    ([key,value]) => dataArray = [...dataArray,value]
                                                );
                                                return dataArray
                                            })}
                                            handleClose = {this.handleClose}
                                            fields = {Object.entries(this.state.tableData[0]).map(item => item[0])}
                                            modalOpen = {this.state.modalOpen}
                                         />) : null }
            </div>
        );
    }
};

DatasetList.propTypes = {
    classes : PropTypes.object.isRequired
};

export default withStyles(datasetListStyle)(DatasetList);