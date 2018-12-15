import { combineReducers } from 'redux';

import DatasetHandler from './DatasetReducers';
import LoginHandler from './LoginReducers';
import DrawerHandler from './DrawerReducer';
import ReportHandler from './ReportReducers';
import DashboardHandler from './DashboardReducers';

const RootReducers = combineReducers({
    dataset : DatasetHandler,
    login : LoginHandler,
    drawer : DrawerHandler,
    report : ReportHandler,
    dashboard : DashboardHandler
});

export default RootReducers;