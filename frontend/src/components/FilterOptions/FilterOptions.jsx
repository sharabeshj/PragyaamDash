import React from 'react';
import Datetime from 'react-datetime';
import TagsInput from 'react-tagsinput';
import nouislider from 'nouislider';

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

import filterOptionsStyle from '../../assets/jss/frontend/components/filterOptionsStyle';

class FilterOptions extends React.Component{
    constructor(props){
        super(props);
        this.state= {
            measureOperation : ['SUM', 'COUNT', 'COUNT DISTINCT', 'MAX', 'MIN', 'AVERAGE']
        }
    }

    componentDidMount(){
        nouislider.create(this.refs.ySlider,{
            start: [this.props.yLen],
            connect: [true,false],
            step: 1,
            range: { min: 0, max: this.props.yLen }
        });
        nouislider.create(this.refs.xSlider, {
            start: [0,this.props.xLen],
            connect: [false, true, false],
            step: 1,
            range: { min: 0, max: this.props.xLen }
        });
    }

    render(){
        const { classes } = this.props;

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
                                                        onChange={this.handleFilterToggle}
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
                                <br />
                                <br />
                                <GridContainer>
                                    <GridItem xs={12} sm={12} md={6}>
                                        <legend>Measure Operation</legend>
                                        <GridContainer>
                                            <GridItem xs={12} sm={6} md={6} lg={6}>
                                                <CustomDropdown 
                                                    hoverColor="info"
                                                    buttonText="Measure Operation"
                                                    buttonProps = {{
                                                        round: true,
                                                        fullWidth: true,
                                                        style: { marginBottom : "0" },
                                                        color: "info"
                                                    }}
                                                    dropdownHeader="Select Operation"
                                                    dropdownList={this.state.measureOperation.map(key => (
                                                        <div key = {key} onClick={() => this.props.handleOperationChange(key)}>key</div>
                                                    ))}
                                                />
                                            </GridItem>
                                        </GridContainer> 
                                    </GridItem>
                                </GridContainer>
                                <br />
                                <br />
                                <GridContainer>
                                    <GridItem xs = {12} sm ={12} md = {12}>
                                        <legend>Range Optimizer</legend>
                                        <div className="slider-info" ref="ySlider"/>
                                        <br />
                                        <div  className="slider-success" ref="xSlider"/>
                                    </GridItem>
                                </GridContainer>
                            </CardBody>
                        </Card>
                    </GridItem>
                </GridContainer>
            </div>
        );
    }
}

export default withStyles(filterOptionsStyle)(FilterOptions);