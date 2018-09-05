import React,{Component} from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import {
    DiagramWidget,
    DiagramEngine,
    DefaultLinkFactory,
    DefaultNodeFactory,
    DefaultNodeModel,
    DefaultPortModel
} from 'storm-react-diagrams';
import { connect } from 'react-redux';
import axios from 'axios';


import { withStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import { Divider, Typography, Radio } from '../../../node_modules/@material-ui/core';

import GridItem from '../../components/Grid/GridItem';
import GridContainer from '../../components/Grid/GridContainer';
import OptionToolbar from '../../components/OptionToolbar/OptionToolbar';
import JoinToolbar from '../../components/JoinToolbar/JoinToobar';
import CustomButtons from '../../components/CustomButtons/Button';
import Aux from '../../hoc/aux/aux';

import datasetStyle from '../../assets/jss/frontend/views/dataset';
import '../../assets/css/srd.css';

import { saveDataset } from '../../store/Actions/ActionCreator';

class Dataset extends Component {
    constructor(props){
        super(props);
        this.state = {
            workSpace : ['workspace_1'],
            selectedWorkSpace : '',
            workSheet : ['Worksheet 1','Worksheet 2'],
            selectedWorkSheet : [],
            worksheetData : [],
            joinData : []
        };
    }

    componentWillMount(){
        this.engine = new DiagramEngine();

        this.engine.registerNodeFactory(new DefaultNodeFactory());
        this.engine.registerLinkFactory(new DefaultLinkFactory());
    }

    componentDidUpdate(prevProps,prevState){
        if(this.props.dataset.fields){
            if(this.props.dataset.fields.length !== prevProps.dataset.fields.length){
                this.props.dataset.fields.map(field => {
                    Object.entries(this.engine.getDiagramModel().getNodes()).forEach(
                        ([key,value]) => {
                            console.log(key);
                            console.log(value);
                            if(value.name === field.worksheet){
                                console.log('hi from inside');
                                Object.entries(this.engine.getDiagramModel().getNode(key).getPorts()).forEach(
                                    ([name,val]) => {
                                        if(!(val.name === 'in-1' || val === 'out-1')) {
                                        if (this.props.dataset.fields.findIndex(x => x.name === val.name )=== -1){
                                            this.engine.getDiagramModel().getNode(key).removePort(val);
                                        }
                                    }
                                    this.forceUpdate();
                                    }
                                );
                                this.engine.getDiagramModel().getNode(key).addPort(new DefaultPortModel(false,`${field.name}`,field.name));
                                this.forceUpdate();
                            }
                        }
                    )
                });
            }
        }
        
    }

    getWorkspace = () => {
        
    }

    handleToggle = value  => {
        const { selectedWorkSheet,workSheet } = this.state;
        const currentIndex = selectedWorkSheet.indexOf(workSheet[value]);
        const newSelectedWorkSheet =  [...selectedWorkSheet]

        if(currentIndex === -1){
            newSelectedWorkSheet.push(workSheet[value]);
        } 
        else {
            newSelectedWorkSheet.splice(currentIndex,1)
        }

        this.setState({
            selectedWorkSheet : newSelectedWorkSheet
        })
    }

    getWorksheetData = (worksheet) => {


        let newWorksheetData = {
            "worksheet_name": "Worksheet 1",
            "worksheet_id": "pgzNw89",
            "userid": "Code Company",
            "rows": "0",
            "columns": "0",
            "last_updated": "5 days"
        };
        newWorksheetData.columnData = {
            "data": [
                {
                    "column": "name",
                    "column_aliases": "name",
                    "type": "text",
                    "tool_tip": "Please Enter the Price",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Price",
                    "column_aliases": "price",
                    "type": "single",
                    "tool_tip": "Please Enter the Price",
                    "required": 1,
                    "static": true,
                    "value": [
                        ""
                    ]
                },
                {
                    "column": "DOB",
                    "column_aliases": "date_of_birth",
                    "type": "text",
                    "tool_tip": "Please Enter the Price",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Sl.No",
                    "column_aliases": "sl_no",
                    "type": "number",
                    "tool_tip": "Please Enter the Number",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Quality No",
                    "column_aliases": "quality_no",
                    "type": "number",
                    "tool_tip": "Please Enter the Number",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Address",
                    "column_aliases": "address",
                    "type": "text",
                    "tool_tip": "Please Enter the Address",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Pincode",
                    "column_aliases": "pincode",
                    "type": "text",
                    "tool_tip": "Please Enter the Pincode",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Zip Code",
                    "column_aliases": "zip_code",
                    "type": "text",
                    "tool_tip": "Please Enter the Zip Code",
                    "required": 1,
                    "static": true,
                    "value": null
                },
                {
                    "column": "Sales Date",
                    "column_aliases": "sales_date",
                    "type": "text",
                    "tool_tip": "Please Enter the Date",
                    "required": 1,
                    "static": true,
                    "value": null
                }
            ],
            "columns": [
                "name",
                "price",
                "date_of_birth",
                "sl_no",
                "quality_no",
                "address",
                "pincode",
                "zip_code",
                "sales_date"
            ]
         }
        this.setState(prevState => {
            const worksheetData = [...prevState.worksheetData,newWorksheetData];
            console.log(worksheetData);
            return {worksheetData : worksheetData};
        });
    }

    handleSubmit = (event) =>  {
        let allJoinData = [];
        Object.entries(this.engine.getDiagramModel().getNodes()).forEach(
            ([key,value]) => {
                if(value.name === "Inner-Join" || value.name === "Right-Join" || value.name === "Left-Join" || value.name === "Outer-Join"){
                    Object.entries(this.engine.getDiagramModel().getNode(key).getPorts()).forEach(
                        ([name,val]) => {
                            console.log('hi');
                            if(val.in){
                                Object.entries(this.engine.getDiagramModel().getNode(key).getPort(name).getLinks()).forEach(
                                    ([linkKey,linkVal]) => {
                                        let JoinData = {
                                            type : value.name,
                                            field : linkVal.sourcePort.name,
                                            worksheet_1 : linkVal.sourcePort.parent.name
                                        }
                                        console.log(JoinData);
                                        Object.entries(this.engine.getDiagramModel().getNode(key).getPorts()).forEach(
                                            ([n,v]) => {
                                                if(!v.in){
                                                    Object.entries(this.engine.getDiagramModel().getNode(key).getPort(n).getLinks()).forEach(
                                                        ([oLinkName,oLinkVal]) => { 
                                                            JoinData.worksheet_2 = oLinkVal.targetPort.parent.name;
                                                            allJoinData = [...new Set([...allJoinData,JoinData])];
                                                        }
                                                    );
                                                }
                                            }
                                        );
                                    }
                                );
                            }
                        }
                    );
                }
            }
        );
        this.props.saveDataset(allJoinData);
    }
    
    render(){
        const {classes} = this.props;

        let list = null;

        let optionToolbar = null;

        let joinToolbar = null;

        let saveOption = null;

        if(Object.keys(this.engine.getDiagramModel().getNodes()).length >= 2){
            joinToolbar = (<JoinToolbar />);
        }

        if(this.state.workSheet !== []){
            list = this.state.workSheet.map((worksheet,key) => {
               return ( <div key = {key}
                        draggable = {true}
                        onDragStart = { event => {
                            console.log('start');
                            event.dataTransfer.setData('worksheet',JSON.stringify({ name : worksheet, key : key }));
                            this.handleToggle(key);
                        }}
                    ><List>
                    <ListItem dense button>
                    <ListItemText primary = {worksheet}/>
                    <ListItemSecondaryAction>
                        <Radio
                            checked  = {this.state.selectedWorkSheet.indexOf(key) !== -1}
                            value = {worksheet}
                            aria-label = {worksheet}
                            name = {worksheet}
                            classes = {{
                                root : classes.radio,
                                checked : classes.radio_checked,
                            }}
                        /> 
                    </ListItemSecondaryAction>
                </ListItem></List></div>)
            })
        }

        if(this.state.worksheetData.length > 0){
            console.log('hi');
            optionToolbar = (
                    <OptionToolbar worksheetData = {this.state.worksheetData}/>
                 );

            saveOption = (
                <div onClick = {this.handleSubmit}>
                    <CustomButtons color = "success">
                        Save
                    </CustomButtons>
                </div>
            );
        }

        const drawer = (
            <Aux>
                <Drawer
                variant = "permanent"
                classes = {{
                    paper : classes.drawerPaper
                }}
                anchor = "left"
            >
                 <div className = {classes.toolbar}>
                    {"DATASET CREATION"}
                 </div>
                 <Divider />
                 <List>
                 {list}
                 </List>
                 <Divider />
                 {joinToolbar}
                 <Divider />
                 {optionToolbar}
            </Drawer>
            </Aux>
        );
        return (
            <div className = {classes.root}>
                <div className = {classes.appFrame}>
                {drawer}
                <div className = {classes.content}>
                    {saveOption}
                    <div
                        className = "diagram-layer"
                        onDrop = { event => {
                            event.preventDefault();
                            let data = JSON.parse(event.dataTransfer.getData('worksheet'));
                            let worksheet = new DefaultNodeModel(data.name);
                            worksheet.addPort(new DefaultPortModel(true,'in-1','X'));
                            worksheet.addPort(new DefaultPortModel(false,'out-1','O'));
                            let points = this.engine.getRelativeMousePoint(event);
                            console.log(worksheet);
                            worksheet.x = points.x;
                            worksheet.y = points.y;
                            this.engine.getDiagramModel().addNode(worksheet);
                            console.log(this.engine.getDiagramModel());
                            this.forceUpdate ();
                            this.getWorksheetData(data.name);
                        
                        }}
                        onDragOver = { event => {
                            event.preventDefault();
                        }}
                    >
                        <DiagramWidget diagramEngine= {this.engine}/>
                    </div>
                </div>
                </div>
            </div>
        );
    }
}

Dataset.propTypes = {
    classes : PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
    dataset : state.dataset
});

const mapDispatchToProps = dispatch => {
    return {
        saveDataset : joinData => dispatch(saveDataset(joinData))
    }
}

export default connect(mapStateToProps,mapDispatchToProps)(withStyles(datasetStyle)(Dataset));