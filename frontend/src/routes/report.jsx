import ReportCreate from '../views/Report/ReportCreate/ReportCreate';
import ReportList from '../views/Report/ReportList/ReportList';

const reportRoutes = [
    {
        path : "/report/reportCreate",
        component : ReportCreate
    },
    {
        path : "/",
        component : ReportList
    }
];

export default reportRoutes;