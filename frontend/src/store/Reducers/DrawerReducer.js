import * as ActionTypes from '../Actions/Actions';

const DrawerHandler = (state = { mobileOpen : false, miniActive : false },action) => {
    switch(action.type){
        case ActionTypes.MOBILE_RESIZE:
            return {
                ...state,
                mobileOpen : action.mobileOpen
            }
        case ActionTypes.DRAWER_TOGGLE:
            return {
                ...state,
                mobileOpen : !state.mobileOpen
            }
        case ActionTypes.DRAWER_TOGGLE_ON_UPDATE:
            return {
                ...state,
                mobileOpen : action.mobileOpen
            }
        case ActionTypes.SIDEBAR_MINI_TOGGLE:
            return {
                ...state,
                miniActive : !state.miniActive
            }
        default:
            return {
                ...state
            }
    }
}

export default DrawerHandler;