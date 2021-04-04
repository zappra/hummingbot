# distutils: language=c++

from hummingbot.core.time_iterator cimport TimeIterator


cdef class ScriptIterator(TimeIterator):
    cdef:
        str _script_file_path
        object _strategy
        object _markets
        object _event_pairs
        object _order_filled_forwarder
        object _did_complete_buy_order_forwarder
        object _did_complete_sell_order_forwarder
        object _script_module
        bint _live_updates
        object _ev_loop
        object _script_adapter
        object _listen_to_child_task
        bint _is_unit_testing_mode
        object _order_book_trade_listener
        object _all_total_balances
        object _all_available_balances

    cdef c_update_balances(self)
