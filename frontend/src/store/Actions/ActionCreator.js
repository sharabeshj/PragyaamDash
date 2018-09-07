import * as ActionTypes from './Actions';
import Axios from 'axios';

export const workspaceAdd = (workspaceName) => {
    return {
        type : ActionTypes.WORKSPACE_ADD,
        workspaceName : workspaceName
    }
}

export const fieldAdd = fields => {
    return {
        type : ActionTypes.FIELD_ADD,
        fields : fields
    }
}

const saved = data => {
    return {
        type : ActionTypes.SAVED,
        joins : data
    }
}

const saveError = error => {
    return {
        type : ActionTypes.SAVE_ERROR,
        error : error
    }
}

const save = (joinData,state) => {
    return dispatch => {
        console.log(state());
        const postData = {
            url : 'http://127.0.0.1:8000/api/datasets/',
            method : 'post',
            data : JSON.stringify({
                name : 'dataset_2',
                fields : state().dataset.fields,
                tables : [
                    {
                        name : "Worksheet 1",
                    },
                    {
                        name : "Worksheet 2"
                    }
                ],
                joins : joinData
            }),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        return Axios(postData) .then((res) => dispatch(saved(joinData))) .catch(e => dispatch(saveError(e)));
    }
}

export const saveDataset = joinData => {
    return (dispatch,getState) => dispatch(save(joinData,getState))
}