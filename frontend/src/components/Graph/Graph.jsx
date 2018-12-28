import React from 'react';
import Chart from 'chart.js';
import ReactDOM from 'react-dom';
import _ from 'lodash';

import CardBody from '../Card/CardBody';

class Graph extends React.Component{
    constructor(props){
        super(props);
        this.chart = null;
        this.state = {
            width : props.width,
            height : props.height
        }
    }

    componentDidMount(){
        this.setGraph();
    }
    componentDidUpdate(prevProps, prevState){
        if(!_.isEqual(this.props, prevProps)){
            let element = ReactDOM.findDOMNode(this.refs.chart);
            let ctx = element.getContext("2d");
            this.setGraph();
        }
    }

    setGraph = () => {
        if(this.chart != null) this.chart.destroy();
        let element = ReactDOM.findDOMNode(this.refs.chart);
        let ctx = element.getContext("2d");
        this.chart = new Chart(ctx, {
            type : this.props.type,
            data : this.props.data,
            options : this.props.options
        })

    }

    render() {
        return(<CardBody index = {this.props.index ? this.props.index : "none"}><canvas index = {this.props.index ? this.props.index : "none"} ref={"chart"} width = {this.state.width} height = {this.state.height}></canvas></CardBody>)
    }

}

export default Graph;