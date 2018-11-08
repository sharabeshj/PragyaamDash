import ReportToolbar from '../components/ReportToolbar/ReportToolbar';
import ReportList from '../views/Report/ReportList/ReportList';

const reportRoutes = [
    {
        path : "/reportCreate",
        component : ReportToolbar
    },
    {
        path : "/reportList",
        component : ReportList
    }
];

export default reportRoutes;