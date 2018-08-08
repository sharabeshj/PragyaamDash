import React , {Component} from 'react';
import PropTypes from 'prop-types';
import { Input,Icon,AutoComplete }from 'antd';
import classNames from 'classnames';
import Debounce from 'lodash-decorators/debounce';
import Bind from 'lodash-decorators/bind';

import styles from '../../assets/less/components/headerSearch.less';

export default class HeaderSearch extends Component {
    static propTypes = {
        className : PropTypes.string,
        placeholder : PropTypes.string,
        onSearch : PropTypes.func,
        onPressEnter : PropTypes.func,
        defaultActiveFirstOption : PropTypes.bool,
        dataSource : PropTypes.array,
        defaultOpen : PropTypes.bool,
    };

    static defaultProps = {
        defaultActiveFirstOption : false,
        onPressEnter : () => {},
        onSearch : () => {},
        className : '',
        placeholder : '',
        dataSource : [],
        defaultOpen : false,
    };

    constructor(props){
        super(props);
        this.state = {
            searchMode : props.defaultOpen,
            value : '',
        };
    }

    onKeyDown = e => {
        if(e.key === 'Enter'){
            this.debouncePressEnter();
        }
    };

    onChange = value => {
        this.setState({ value });

        const { onChange } = this.props;
        if(onChange){
            onChange();
        }
    };

    enterSearchMode = () => {
        this.setState({ searchMode : true }, () => {
            const { searchMode } = this.state;
            if(searchMode) {
                this.input.focus();
            }
        });
    };

    debouncePressEnter() {
        const { onPressEnter } = this.props;
        const [ value ] = this.state;

        onPressEnter(value);
    }

    @Bind()
    @Debounce(500, {
        leading : true,
        trailing : false,
    })

    render(){
        const { className,placeholder,...restProps } = this.props;

        const { searchMode,value } = this.state;
        delete restProps.defaultOpen;
        const inputClass = classNames(styles.input,{
            [styles.show] : searchMode,
        });
        return (
            <span className = {classNames(className,styles.headerSearch)} onClick = {this.enterSearchMode}>
                <Icon type = "search" key = "Icon"/>
                <AutoComplete
                    key = "AutoComplete"
                    {...restProps}
                    className = {inputClass}
                    value = {value}
                    onChange = {this.onChange}
                >
                    <Input
                        placeholder = {placeholder}
                        ref = {node => {
                            this.input = node;
                        }}
                        onKeyDown = { this.onKeyDown }
                        onBlur = { this.leaveSearchMode }
                    />
                </AutoComplete>
            </span>
        )
    }
}