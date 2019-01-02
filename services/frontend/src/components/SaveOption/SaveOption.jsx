import React from 'react';

import CustomInput from '../CustomInput/CustomInput';
import CustomButtons from '../CustomButtons/Button';
import GridContainer from '../Grid/GridContainer';
import GridItem from '../Grid/GridItem';

const SaveOption = props => {
    console.log(props);
    return (
        <GridContainer>
            <GridItem xs = {6} sm = {3} md = {2} lg = {2}>
                <CustomButtons color = "success" onClick = {props.handleSubmit}>
                    Save
                </CustomButtons>
            </GridItem>
            <GridItem xs = {6} sm = {6} md = {4} lg = {4}>
                <CustomInput 
                    labelText = "Dataset Name"
                    id = "name"
                    success
                    formControlProps = {{
                        fullWidth : true
                    }}
                    onChange = {props.handleChange}
                    value = {props.content}
                />
            </GridItem>
        </GridContainer>
    );
};




export default SaveOption;