import React from 'react';
import Datetime from 'react-datetime';
import TagsInput from 'react-tagsinput';

import { withStyles } from  '@material-ui/core/styles';
import FormControl from "@material-ui/core/FormControl";
import FormControlLabel from "@material-ui/core/FormControlLabel";
import InputLabel from "@material-ui/core/InputLabel";
import Switch from "@material-ui/core/Switch";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";

import Today from '@material-ui/icons/Today';

import GridContainer from '../../components/Grid/GridContainer';
import GridItem from '../../components/Grid/GridItem';
import CustomDropdown from '../../components/CustomDropdown/CustomDropdown';
import Card from '../../components/Card/Card';
import CardHeader from '../Card/CardHeader';
import CardIcon from '../Card/CardIcon';
import CardBody from '../Card/CardBody';
import CustomButton from '../CustomButtons/Button';
import FilterHiddenOptions from './FilterHiddenOptions';

import filterOptionsStyle from '../../assets/jss/frontend/components/filterOptionsStyle';

class FilterOptions extends React.Component{
    constructor(props){
        super(props);
        this.state= {
            measureOperation : ['SUM', 'COUNT', 'COUNT DISTINCT', 'MAX', 'MIN', 'AVERAGE'],
            yRange : [0, this.props.yLen],
            xRange : [0, this.props.xLen],
            selectedOperation : ''
        }
    }

    handleSelectedOperation = key => {
        this.setState({ selectedOperation : key });
    }

    handleXRange = (values) => {
        this.setState({ xRange : values });
    }

    handleYRange = values => {
        this.setState({ yRange : values });
    }

    handleFilterOptions = () => {
        this.props.handleFilterOptions({ ...this.state });
    }

    render(){
        const { classes } = this.props;
        let filters  = null;
        if(this.props.filterChecked){
            filters = (<FilterHiddenOptions 
                yLen = {this.state.yLen}
                xLen = {this.state.xLen}
                yRange = {this.state.yRange}
                xRange = {this.state.xRange}
                measureOperation = {this.state.measureOperation}
                handleXRange = {this.handleXRange}
                handleYRange = {this.handleYRange}
                handleSelectedOperation = {this.handleSelectedOperation}
                handleFilterOptions = {this.handleFilterOptions}
                />);
        }
        return (
            <div>
                <GridContainer>
                    <GridItem xs={12} sm={12} md={6}> 
                        <Card>
                            <CardBody>
                                <br />
                                <br />
                                <GridContainer>
                                    <GridItem xs={6} sm={6} md={3}>
                                        <legend>Filters</legend>
                                        <div className={classes.block}>
                                            <FormControlLabel 
                                                control={
                                                    <Switch 
                                                        checked={this.props.filterChecked}
                                                        onChange={this.props.handleFilterToggle}
                                                        value="filter"
                                                        classes={{
                                                            switchBase: classes.switchBase,
                                                            checked: classes.switchChecked,
                                                            icon: classes.switchIcon,
                                                            iconChecked: classes.switchIconChecked,
                                                            bar: classes.switchBar
                                                        }}
                                                    />
                                                }
                                                classes = {{
                                                    label: classes.label
                                                }}
                                                label={`filter is ${'on' ? this.props.filterChecked : 'off'}`}
                                            />
                                        </div>
                                    </GridItem>
                                </GridContainer>
                                {filters}
                            </CardBody>
                        </Card>
                    </GridItem>
                </GridContainer>
            </div>
        );
    }
}

export default withStyles(filterOptionsStyle)(FilterOptions);