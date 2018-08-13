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


import { withStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';

import GridItem from '../../components/Grid/GridItem';
import GridContainer from '../../components/Grid/GridContainer';
import Card from '../../components/Card/Card';
import CardHeader from '../../components/Card/CardHeader';
import CardBody from '../../components/Card/CardBody';
import { Divider, Typography, Radio } from '../../../node_modules/@material-ui/core';

import datasetStyle from '../../assets/jss/frontend/views/dataset';
import '../../assets/css/srd.css';

class Dataset extends Component {
    constructor(props){
        super(props);
        this.state = {
            workSpace : ['workspace_1'],
            selectedWorkSpace : '',
            workSheet : ['worsheet_1','worksheet_2'],
            selectedWorkSheet : []
        };
    }

    componentWillMount(){
        this.engine = new DiagramEngine();
        this.engine.registerNodeFactory(new DefaultNodeFactory());
        this.engine.registerLinkFactory(new DefaultLinkFactory());
    }

    componentDidMount(){
        // this.getWorkspace();
    }

    getWorkspace = () => {
        this.setState({ workSpace : 'workspace_1'})
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

    // getWorksheets = (workSpace) => {
    //     this.setState({ ...this.state.workSheet,[{ name : 'worksheet_1'}] })
    // }

    render(){
        const {classes} = this.props;

        let list = null;

        if(this.state.workSheet !== []){
            list = this.state.workSheet.map((worksheet,key) => {
               return ( <div key = {key}
                        draggable = {true}
                        onDragStart = { event => {
                            event.dataTransfer.setData('worksheet',JSON.stringify({ name : worksheet, key : key }));
                            this.handleToggle(key);
                        }}
                    >
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
                </ListItem></div>)
            })
        }

        const drawer = (
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
                 
            </Drawer>
        )
        return (
            <div className = {classes.root}>
                <div className = {classes.appFrame}>
                {drawer}
                <main className = {classes.content}>
                    {/* <div className = {classes.toolbar}/> */}
                    <div
                        className = "diagram-layer"
                        onDrop = { event => {
                            event.preventDefault();
                            let data = JSON.parse(event.dataTransfer.getData('worksheet'));
                            let worksheet = new DefaultNodeModel(`worksheet ${data.key + 1}`);
                            worksheet.addPort(new DefaultPortModel(true,'in-1','X'));
                            // worksheet.addPort(new DefaultPortModel(false,'out-1','O'));
                            let points = this.engine.getRelativeMousePoint(event);
                            console.log(points);
                            worksheet.x = points.x;
                            worksheet.y = points.y;
                            this.engine.getDiagramModel().addNode(worksheet);
                            this.forceUpdate();
                        }}
                        onDragOver = { event => {
                            event.preventDefault();
                        }}
                    >
                        <DiagramWidget diagramEngine= {this.engine}/>
                    </div>
                </main>
         
                </div>
            </div>
        );
    }
}

Dataset.propTypes = {
    classes : PropTypes.object.isRequired,
}

export default withStyles(datasetStyle)(Dataset);