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
                username : 'shubham',
                password : 'Shubham_123'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        return Axios(postData).then((res) => dispatch(saved(name,joinData))).catch(e => dispatch(saveError(e)));
    }
}

const validate = loginData => {
    return dispatch => {
        const postData = {
            url : 'http://pragyaambackend.mysnippt.com/api/login',
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

const loadSuccess = (data, options) => {
    delete options.type;
    return {
        type : ActionTypes.DATA_LOAD,
        data : data,
        options : options
    }
}

const loadError = err => {
    return {
        type : ActionTypes.DATA_LOAD_ERROR,
        error : err
    }
}

const loadData = data => {
    return dispatch => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/report_generate/',
            method : 'POST',
            data : JSON.stringify(data),
            auth :  {
                username : 'shubham',
                password : 'Shubham_123'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => dispatch(loadSuccess(res.data.data, data)))
            .catch(err => dispatch(loadError(err)));
    }
} 

export const handleDataLoad = (data) => {
    return (dispatch,getState) => (dispatch(loadData(data)))
}

export const handleDefaultDataLoad = (data,type) => {
    return {
        type : ActionTypes.DEFAULT_DATA_LOAD,
        data : data.data,
        options : {
            type: type,
            reportOptions : data.options
        }
    }
}

export const handleClearReportData = () => {
    return { 
        type : ActionTypes.DATA_LOAD_ERROR
    }
}

const dashLoadSuccess = (data, id) => {
    return {
        type : ActionTypes.DASH_LOAD_DATA,
        data : data,
        id : id
    }
}

const dashLoadError = (err) => {
    return {
        type : ActionTypes.DASH_LOAD_ERROR,
        error : err
    }
}

const reportLoadSuccess = (data, id) => {
    return {
        type : ActionTypes.REPORT_LOAD_DATA,
        data : data,
        id : id
    }
}

const reportLoadError = (err) => {
    return {
        type : ActionTypes.REPORT_LOAD_ERROR,
        errror : err
    }
}

const dashLoadData = (data, id) => {
    return dispatch => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/report_generate/',
            method : 'POST',
            data : JSON.stringify(data.report_options),
            auth :  {
                username : 'shubham',
                password : 'Shubham_123'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => dispatch(dashLoadSuccess(res.data.data, id)))
            .catch(err => dispatch(dashLoadError(err)));
    }
}

const reportLoadData = (data,id) => {
    return dispatch => {
        const postData = {
            url : 'http://127.0.0.1:8000/api/report_generate/',
            method : 'POST',
            data : JSON.stringify(data.report_options),
            auth :  {
                username : 'shubham',
                password : 'Shubham_123'
            },
            headers : { 'Content-Type' : 'application/json'}
        };
        Axios(postData)
            .then(res => dispatch(reportLoadSuccess(res.data.data, id)))
            .catch(err => dispatch(reportLoadError(err)));
    }
}

export const handleDashCustomizeFetchData = (data, id) => {
    return (dispatch,getState) => (dispatch(dashLoadData(data, id)));
}

export const clearDashCustomizeData = () => {
    return {
        type : ActionTypes.DASH_LOAD_ERROR
    }
}

export const handleReportFetchData = (data,id) => {
    return (dispatch,getState) => (dispatch(reportLoadData(data, id)));
}

export const clearReportDataList = () => {
    return {
        type : ActionTypes.REPORT_LOAD_ERROR
    }
}