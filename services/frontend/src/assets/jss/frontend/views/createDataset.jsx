import {
    drawerWidth,
} from '../../frontend';
import green from '@material-ui/core/colors/green';

const CreateDatasetStyle = theme => ({
    root: {
                display: "flex"
              },
              appBar: {
                zIndex: theme.zIndex.drawer + 1
              },
              drawer: {
                width: 240,
                flexShrink: 0,
                width: 240,
                flexShrink: 0,
              },
              drawerPaper: {
                width: 240,
                position : 'absolute',
                zIndex:100,
                paddingTop:"22%",
                overflowX:"hidden",
                overflowY:"auto",
                backgroundColor:"#F2F1F1"
        
              },
              listItemText:{
                fontSize:'11px',//Insert your required size
              },
              content: {
        flexGrow : 1,
        width : '100%',
        backgroundColor : "white",
      },
      appFrame : {
            height : '100%',
            zIndex : 1,
            overflow : 'auto',
            position : 'relative',
            display : 'flex',
            width : '100%',
        },
    // },
    // radio_checked : {},
    // listStyle : {
    //     zIndex : -1
    // }
});

export default CreateDatasetStyle;