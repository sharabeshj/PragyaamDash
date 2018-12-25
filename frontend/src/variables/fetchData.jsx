import Axios from 'axios';

const handleFetchData = (data) => {
    const postData = {
        url : 'http://127.0.0.1:8000/api/report_generate/',
        method : 'POST',
        data : JSON.stringify(data.report_options),
        auth :  {
            username : 'sharabesh',
            password : 'shara1234'
        },
        headers : { 'Content-Type' : 'application/json'}
    };
    return Axios(postData)
}

export default handleFetchData;