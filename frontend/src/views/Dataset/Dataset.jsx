import React,{Component} from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';

import { withStyles } from '@material-ui/core/styles';
import Drawer from '@material-ui/core/Drawer';
import List from '@material-ui/core/List';

import GridItem from '../../components/Grid/GridItem';
import GridContainer from '../../components/Grid/GridContainer';
import Card from '../../components/Card/Card';
import CardHeader from '../../components/Card/CardHeader';
import CardBody from '../../components/Card/CardBody';
import { Divider, Typography } from '../../../node_modules/@material-ui/core';

import datasetStyle from '../../assets/jss/frontend/views/dataset';

class Dataset extends Component {
    render(){
        const {classes} = this.props;
        const {anchor} = 'left';

        const drawer = (
            <Drawer
                variant = "permanent"
                classes = {{
                    paper : classes.drawerPaper
                }}
                anchor = {anchor}
            >
                 <div className = {classes.toolbar}>
                    DATASET CREATION
                 </div>
                 <Divider />
                 list
            </Drawer>
        )
        return (
            <div className = {classes.root}>
                <div className = {classes.appFrame}>
                {drawer}
                <main className = {classes.content}>
                    <div className = {classes.toolbar}/>
                    <Typography>hello</Typography>
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