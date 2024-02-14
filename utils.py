# --- LIBRARIES ------------------------------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import plotly.express as px
from datetime import date
from streamlit_option_menu import option_menu

# --- READ DATA ------------------------------------------
# @st.cache_data(ttl=1) #Refresh every n seconds
def read_data(conn = st.session_state['conn'], username = st.session_state['username'], gsheet='doubledeg', ncols=6):
    """Read data from Google Sheets dataset into a dataframe and save it in the session state as 'data'"""
    data = conn.read(usecols=list(range(ncols)), worksheet=gsheet)
    if gsheet == 'inversiones':
        data['Opening date'] = pd.to_datetime(data['Opening date'], yearfirst=True).dt.strftime('%Y-%m-%d') # Leave as string to avoid bugs of date format changing
        data['Closing date'] = pd.to_datetime(data['Closing date'], yearfirst=True).dt.strftime('%Y-%m-%d') # Leave as string to avoid bugs of date format changing
    else:
        data['date'] = pd.to_datetime(data['date'], yearfirst=True).dt.strftime('%Y-%m-%d') # Leave as string to avoid bugs of date format changing
    
    if username == 'other':
        data['amount'] = data['amount']*np.random.rand(len(data)) # Randomize amount for 'other' user
        data.drop(columns=['description'], inplace=True) # Remove description column for 'other' user
    st.session_state['data'] =  data.dropna(how='all') # Remove extra rows that are actually empty

# --- SHEET SELECTION ------------------------------------------
def get_sheet_and_cols(selection: str):
    """Get the Google Sheet, number of columns to read and currency for the selected database"""
    if selection=='Italy':
        gsheet = 'doubledeg'
        ncols = 6
        currency = '\N{euro sign}'
    elif selection=='Colombia':
        gsheet = 'personal'
        ncols = 6
        currency = '$'
    elif selection=='Investments':
        gsheet = 'inversiones'
        ncols = 8
        currency = '$'
    return gsheet, ncols, currency

def on_change(key):  # Callback for sheet_menu() -> Update the session state with the selected sheet and load the corresponding data
    selection = st.session_state[key]
    gsheet, ncols, _ = get_sheet_and_cols(selection)
    st.session_state['gsheet'] = gsheet
    read_data(gsheet = gsheet, ncols = ncols)

def sheet_menu():
    selected = option_menu(
        menu_title=None,
        options=['Italy','Colombia','Investments'],
        icons=['airplane','house','cash'],
        default_index=0,
        menu_icon='cast',
        orientation='horizontal',
        key='menu_1',
        on_change=on_change
    )
    return selected

def get_categories(sheet: str) -> list:
    """Get the different possible categories of spending/investments for the selected sheet"""
    if sheet=="doubledeg":
        categories = ['Administrativo','Alojamiento','Celular','Comida U','Compras varias',
                        'Mercado','Salidas','Salud','Transporte','Viajes']
    elif sheet=="personal":
        categories = ['Ahorros','Salidas','Transporte','Compras','Viajes','Salario','Clases particulares']
    elif sheet=="inversiones":
        categories = ['Acciones','Fondo','Divisas','ETF','Particular']
    return categories

# --- show raw data for doubledeg and personal --------------------------
def show_raw_data(df: pd.DataFrame, gsheet: str, currency: str) -> pd.DataFrame:
    """Show the raw data in a table depending on the sheet selected. Pass st.session_state['data'], st.session_state['gsheet'] and currency as inputs
      and returns the table with the modifications"""
    
    if gsheet == 'inversiones':
        df = df.copy().astype({'Amount opening':float,'Amount closing':float}).sort_values(by='Opening date',ascending=False)
        df['Opening date'] = pd.to_datetime(df['Opening date'], yearfirst=True)
        df['Closing date'] = pd.to_datetime(df['Closing date'], yearfirst=True)
        edited_df = st.data_editor(df, hide_index=True,
                                    column_config={'Amount opening':st.column_config.NumberColumn("Amount opening", format=f"{currency} %.0f"),
                                                    'Opening date':st.column_config.DateColumn('Opening date'),
                                                    'Amount closing':st.column_config.NumberColumn("Amount closing", format=f"{currency} %.0f"),
                                                    'Closing date':st.column_config.DateColumn('Closing date'),
                                                    'Type':st.column_config.SelectboxColumn('Type', help='Type of investment', required = True, options=get_categories(gsheet))},
                                    num_rows='dynamic')
    else:  # sheets personal and doubledeg
        df = df.copy().astype({'recurrent':bool,'include':bool}).sort_values(by='date',ascending=False)
        df['date'] = pd.to_datetime(df['date'], yearfirst=True)
        categories = get_categories(gsheet)
        edited_df = st.data_editor(df, hide_index=True,
                                    column_config={'amount':st.column_config.NumberColumn("Amount", format=f"{currency} %.1f"),
                                                    'date':st.column_config.DateColumn('Date'),
                                                    'category':st.column_config.SelectboxColumn('Category', help='Type of spending', required = True, options=categories),
                                                    'recurrent':st.column_config.CheckboxColumn('Recurrent',help='Is it recurrent?',default=True),
                                                    'inclue':st.column_config.CheckboxColumn('Include',help='Include it in monthly averages?',default=True)},
                                    num_rows='dynamic')
    return edited_df

def monthly_total_spending(monthly, currency, recurrent=[True,False], include=[True]):
    """Print the total amount spent this month and the balance, depending on the sheet selected. Pass the data st.session_state['data'] and the currency as inputs"""

    today_m = date.today().month
    today_y = date.today().year

    if st.session_state['gsheet'] != 'inversiones':   # If doubledeg or personal
        mask = (monthly['recurrent'].isin(recurrent))&(monthly['include'].isin(include))
        filtered = monthly[mask] # Apply filters
        filtered['date'] = pd.to_datetime(filtered['date'], yearfirst=True)
        this_month = filtered[(filtered.date.dt.month == today_m) & (filtered.date.dt.year == today_y)] # Get only data from current month

        if st.session_state['gsheet'] == 'doubledeg':
            this_month_sum = this_month['amount'].sum()  # Total amount spent this month
            st.write('This month you have spent ' +currency + '{:,.0f}'.format(this_month_sum))

        elif st.session_state['gsheet'] == 'personal':
            this_month_sum = -this_month[this_month['amount'] < 0]['amount'].sum()  # Total amount spent this month (negative values represent expenses)
            st.write('This month you have spent ' +currency + '{:,.0f}'.format(this_month_sum))
            this_month_balance = this_month['amount'].sum()  # Total balance for this month (considering expenses and income)
            st.write('This month your balance is ' +currency + '{:,.0f}'.format(this_month_balance))
        return filtered

    elif st.session_state['gsheet'] == 'inversiones':
        monthly['Opening date'] = pd.to_datetime(monthly['Opening date'], yearfirst=True)
        monthly['Closing date'] = pd.to_datetime(monthly['Closing date'], yearfirst=True)
        this_month_open = monthly[(monthly['Opening date'].dt.month == today_m) & (monthly['Opening date'].dt.year == today_y)]
        this_month_close = monthly[(monthly['Closing date'].dt.month == today_m) & (monthly['Closing date'].dt.year == today_y)]
        this_month_open_sum = this_month_open['Amount opening'].sum()
        this_month_close_sum = this_month_close['Amount closing'].sum()
        st.write('This month you have invested ' +currency + '{:,.0f}'.format(this_month_open_sum))
        st.write('This month you have received ' +currency + '{:,.0f}'.format(this_month_close_sum))

# --- ADDING NEW MOVEMENTS -------------------------------------------------------------------------------
def show_input_data(gsheet):
    if gsheet == 'inversiones':
        inv_name = st.text_input('Investment name')
        col1, col2 = st.columns(2)
        platform = col1.text_input('Platform')
        type = col2.selectbox('Type', get_categories(gsheet))
        opening_date = col1.date_input('Opening date').strftime("%Y-%m-%d")
        amount_opening = col2.number_input('Amount opening (COP)')
        comments = st.text_input('Comments')

        new_row = [inv_name,platform,type,opening_date,amount_opening,None,None,comments]  # Leave closing date and Amount closing empty
    else:       # doubledeg and personal
        col1, col2 = st.columns(2)
        date = col1.date_input('Date').strftime("%Y-%m-%d")
        amount = col2.number_input('Amount')
        category = st.selectbox('Category', get_categories(gsheet))
        description = st.text_input('Description')
        col1, col2 = st.columns(2)
        recurrent = col1.checkbox('Recurrent spending', value=True) # If movement is recurrent monthly
        include = col2.checkbox('Include', value=True)              # If want to include movement later in visualizations and aggregations

        new_row = [date,amount,category,description,recurrent,include] # Data for new row

    return new_row

# --- PLOTS ----------------------------------------------------------------------------------------------
# --- Monthly spending plot for personal and doubledeg ------------
def monthly_spending_plot(filtered,include,currency):
    filtered = filtered.set_index('date')
    if False in include: # In order to show different colors
        monthly_agg = filtered.groupby([pd.Grouper(freq='M'), 'include'])['amount'].sum().reset_index(1)
        fig = px.bar(monthly_agg, title='Total monthly spending', text_auto='.0f',color='include',
                    labels={'date':'Month', 'value':f'Amount {currency}'})
    else:
        monthly_agg = filtered.groupby(pd.Grouper(freq='M'))['amount'].sum()
        monthly_agg.index = monthly_agg.index.strftime("%Y-%m")
        fig = px.bar(monthly_agg, title='Total monthly spending', text_auto='.0f',
                    labels={'date':'Month', 'value':f'Amount {currency}'})
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False) # Annotate data
    fig.update_layout(showlegend=False) # Remove legend
    fig.update_xaxes(dtick="M1",tickformat="%b\n%Y") # Show monthly ticks in x-axis
    st.plotly_chart(fig) # Show figure

# --- Heatmap ------------
def get_monthly_heatmap(df: pd.DataFrame):
    fig = px.imshow(df, text_auto=True, aspect="auto")
    fig.update_xaxes(side="top")
    st.plotly_chart(fig, theme=None) # , theme="streamlit"