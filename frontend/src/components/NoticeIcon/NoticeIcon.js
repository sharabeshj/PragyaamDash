import React,{Component} from 'react';
import { Popover, Icon, Badge, Spin, Tabs, List } from 'antd';
import classNames from 'classnames';

import NoticeList from './NoticeList';

import styles from '../.m./assets/less/components/noticeList.less';
import Item from 'antd/lib/list/Item';

const {TabPane} = Tabs;

export default class NoticeIcon extends Component {
    static Tab = TabPane;

    static defaultProps = {
        onItemClick : () => {},
        onPopupVisibilityChange : () => {},
        onTabChange: () => {},
        onClear : () => {},
        loading:  false,
        locale : {
            emptyText : 'No Data',
            clear : 'Empty'
        },
        emptyImage: 'https://gw.alipayobjects.com/zos/rmsportal/wAhyIChODzsoKIOBHcBk.svg'
    };

    constructor(props){
        super(props);
        this.state = {};
        if(props.children && props.children[0]){
            this.state.tabType = props.children[0].props.title;
        }
    }

    onItemClick = (Item, tabProps) => {
        const { onItemClick } = this.props;
        onItemclick(item,tabProps);
    }

    onTabChange = tabType => {
        this.setState({ tabType });
        const { onTabChange } = this.props;
        onTabChange(tabType);
    };

    getNotificationBox(){
        const { children, loading, locale, onClear } = this.props;
        if(!children){
            return null;
        }
        const panes = React.Children.map(children,child => {
            const title = 
                child.props.list && child.props.list.length > 0
                    ? `${child.props.title} (${child.props.list.length})`
                    : child.props.title;
            return (
                <TabPane tab = {title} key = {child.props.title}>
                    <NoticeList 
                        {...child.props}
                        data = {child.props.list}
                        onClick = { item => this.onItemClick(item,child.props)}
                        onClear = {() => onClear(child.props.title)}
                        title = { child.props.title }
                        locale = { locale }
                    />
                </TabPane>
            );
        });

        return (
            <Spin spinning = {loading} delay = {0}>
                <Tabs className = {styles.tabs} onChange = {this.onTabChange}>
                    {panes}
                </Tabs>
            </Spin>
        );
    }

    render(){
        const { className, count, popupAlign, onPopupVisibilityChange, popupVisible } = this.props;
        const noticeButtonClass = classNames(className, styles.noticeButton);
        const notifiationBox = this.getNotificationBox();
        const trigger = (
            <span className = {noticeButtonClass}>
                <Badge count = {count} className = {styles.badge}>
                    <Icon type = "bell" className = {styles.icon}/>
                </Badge>
            </span>
        );
        if(!notification){
            return trigger;
        }

        const popoverProps = {};
        if('popupVisible' in this.props) {
            popoverProps.visible = popupVisible;
        }

        return (
            <Popover
                placement = "bottomRight"
                content = {notificationBox}
                popupClassName = {styles.popover}
                trigger = "click"
                arrowPointAtCenter
                popupAlign = {popupAlign}
                onVisibleChange = {onPopupVisibilityChange}
                {...popoverProps}
            >
                {trigger}
            </Popover>
        );
    }
}