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

export const tableAdd = table => {
    return {
        type : ActionTypes.TABLE_ADD,
        table : table
    }
}

// export const datasetName = name => {
//     return {
//         type : ActionTypes.SAVE_DATASET_NAME,
//         name : name
//     }
// }

const saved = (name,data) => {
    return {
        type : ActionTypes.SAVED
    }
}

const saveError = error => {
    return {
        type : ActionTypes.SAVE_ERROR,
        error : error
    }
}

const loginSuccess = data => {
    if(data.status){
        return {
            type : ActionTypes.LOGIN_SUCCESS,
            data : data.data
        }
    }
}

const loginError = error => {
    return {
        type : ActionTypes.LOGIN_ERROR,
        error : error
    }
}

const save = (name,joinData,state) => {
    return dispatch => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/datasets/',
            method : 'POST',
            data : JSON.stringify({
                name : name,
                fields : state().dataset.fields,
                tables : state().dataset.tables,
                joins : joinData
            }),
            auth :  {
                username : 'sharabesh',
                password : 'shara1234'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        return Axios(postData).then((res) => dispatch(saved(name,joinData))).catch(e => dispatch(saveError(e)));
    }
}

const validate = loginData => {
    return dispatch => {
        const postData = {
            url : 'http://pragyaamfrontend.mysnippt.com/api/login',
            method : 'POST',
            data : JSON.stringify({
                ...loginData
            }),
            headers : { 'Content-Type' : 'application/json'}
        }
        return Axios(postData).then(res => dispatch(loginSuccess(res.data))).catch( e => dispatch(loginError(e)));
    }
}

export const saveDataset = (name,joinData) => {
    return (dispatch,getState) => dispatch(save(name,joinData,getState))
}

export const login = (loginData) => {
    return (dispatch,getState) => dispatch(validate(loginData))
}

export const fieldClear = () => {
    return (dispatch,getState) => dispatch(saveError("error"))
}

export const mobileResizeFunction = () => {
    if(window.innerWidth > 960){
        return {
            type : ActionTypes.MOBILE_RESIZE,
            mobileOpen : false
        }
    }
}

export const handleDrawerToggle = () => {
    return {
        type : ActionTypes.DRAWER_TOGGLE
    }
}

export const handleDrawerToggleOnUpdate = () => {
    return {
        type : ActionTypes.DRAWER_TOGGLE_ON_UPDATE,
        mobileOpen : false
    }
}

export const handleMiniSidebarToggle = () => {
    return {
        type : ActionTypes.SIDEBAR_MINI_TOGGLE
    }
}

// export const getDefaultGraphData = (name) => {
//     return {
//         type : ActionTypes.GRAPH_DEFAULT,
//         name : name
//     }
// }