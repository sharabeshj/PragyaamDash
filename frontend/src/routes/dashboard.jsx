import Storage from '@material-ui/icons/Storage';

import Dataset from '../views/Dataset/Dataset';


const dashboardRoutes = [
//   {
//     path: "/home",
//     sidebarName: "Home",
//     navbarName: "Home",
//     icon:Home,
//     component:HomePage
//   },
//   { 
//     path: "/workspace",
//     sidebarName: "Workspace",
//     navbarName: "Workspace",
//     icon: TableChart,
//     component: WorkspacePage    
//   },
  {
    path: "/dataset",
    sidebarName: "Dataset",
    navbarName: "Dataset",
    icon: Storage,
    component: Dataset
  },
//   {
//     path: "/layer",
//     sidebarName: "Layers",
//     navbarName: "Layers",
//     icon: Layers,
//     component: Layer
//   },
//   {
//     path: "/report",
//     sidebarName: "Report",
//     navbarName: "Report",
//     icon: PhotoFilter,
//     component: Report
//   },
  { redirect: true, path: "/", to: "/dashboard", navbarName: "Redirect" }
];

export default dashboardRoutes;
