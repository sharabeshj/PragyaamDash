import React from 'react';
import noUiSlider from 'nouislider';

import GridContainer from '../Grid/GridContainer';
import GridItem from '../Grid/GridItem';
import CustomButton from '../CustomButtons/Button';
import CustomDropdown from '../CustomDropdown/CustomDropdown';


class FilterHiddenOptions extends React.Component{
    constructor(props){
        super(props);
    }

    componentDidMount(){
        console.log(this.refs.ySlider);
        noUiSlider.create(this.refs.ySlider,{
            start: [this.props.yLen],
            connect: [true,false],
            step: 1,
            range: { min: this.props.yRange[0], max: this.props.yRange[1] }
        });
        noUiSlider.create(this.refs.xSlider, {
            start: [0,this.props.xLen],
            connect: [false, true, false],
            step: 1,
            range: { min: this.props.xRange[0], max: this.props.xRange[1] }
        });

        const self = this;
        this.refs.ySlider.noUiSlider.on('update', function(values,handle){
            console.log(values);
            if(typeof values[handle] != "undefined"){
                self.props.handleYRange(values[handle]);
            }
        });

        this.refs.xSlider.noUiSlider.on('update',function(values,handle){
            if(typeof values[handle] != "undefined"){
                self.props.handleXRange(values[handle]);
            }
        })
    }

    render(){
        return(
            <div><br />
                <br />
                <GridContainer>
                    <GridItem xs={12} sm={12} md={6}>
                        <legend>Measure Operation</legend>
                        <GridContainer>
                            <GridItem xs={12}>
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
                                    dropdownList={this.props.measureOperation.map(key => (
                                        <div key = {key} onClick={() => this.props.handleSelectedOperation(key)}>{key}</div>
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
                        <div className="slider-success" ref="xSlider"/>
                    </GridItem>
                </GridContainer>
                <br />
                <br />
                <GridContainer>
                    <GridItem xs={6} sm = {6} md = {3}> 
                        <CustomButton size={'sm'} color = 'warning' onClick={e => this.props.handleFilterOptions()}>
                            Save
                        </CustomButton>
                    </GridItem>
                    </GridContainer></div>
        );
    }
}

export default FilterHiddenOptions;