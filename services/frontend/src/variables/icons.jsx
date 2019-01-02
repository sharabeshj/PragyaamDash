import Filter1 from '@material-ui/icons/Filter1';
import Filter2 from '@material-ui/icons/Filter2';
import Filter3 from '@material-ui/icons/Filter3';
import Filter4 from '@material-ui/icons/Filter4';
import Filter5 from '@material-ui/icons/Filter5';
import Filter6 from '@material-ui/icons/Filter6';
import Filter7 from '@material-ui/icons/Filter7';
import Filter8 from '@material-ui/icons/Filter8';
import Filter9 from '@material-ui/icons/Filter9';

const Icons = (key) => {
        switch(key){
            case 0:
                return Filter1;
            case 1:
                return Filter2;
            case 2:
                return Filter3;
            case 3:
                return Filter4;
            case 4:
                return Filter5;
            case 5:
                return Filter6;
            case 6:
                return Filter7;
            case 7:
                return Filter8;
            case 8:
                return Filter9;
            default:
                return null;
        }
};

export default Icons;