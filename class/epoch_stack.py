from posture_stack_abc import ABCPostureStack
from process import Process

import pandas as pd
import numpy as np
import math
import datetime

class EpochStack(ABCPostureStack, Process):
    def __init__(self, processing_type='epoch'):
        self.processing_type = processing_type
        self.posture_stack = None
        self.posture_stack_duration = None
        self.posture_stack_epoch_type = None

    def get_data(self, activity_monitor):
        self.events_to_process = activity_monitor.event_data

    def show_stack(self):
        print('Posture Stack')
        print('----------')
        print('Unique class values')
        print(self.posture_stack.Event_Code.unique())
        print('----------')
        print('Posture stack duration')
        print(f"The posture stacks contains {self.posture_stack_duration} seconds of data.")
        print('----------')

    def create_stack(self, stack_type, subset_of_data = None):
        self.posture_stack_epoch_type = stack_type
        if self.processing_type == 'epoch':
            event_data = pd.read_csv(self.events_to_process)
            # subset of data for testing
            if subset_of_data:
                print(f'Using subset of data with just over {subset_of_data} events')
                event_data = event_data.iloc[:subset_of_data]
            event_data.Time = pd.to_datetime(event_data.Time, unit='d', origin='1899-12-30')
            epochSize = 15
            windowShift = 5
            startTime = event_data.Time.iloc[0]
            endTime = event_data.Time.iloc[-1]
            totalTime = ((endTime - startTime).total_seconds()) + event_data['Interval (s)'].iloc[-1]
            self.posture_stack_duration = totalTime
            numOfEvents = math.ceil(totalTime / windowShift)
            column_names = ['Start_Time', 'Finish_Time', 'Event_Code']
            posture_stack = pd.DataFrame(0, index=np.arange(numOfEvents), columns=column_names)
            for i in range(numOfEvents):
                self.print_progress_bar(i+1, numOfEvents, 'Creating posture stack progress:')
                posture_stack.iloc[i, 0] = startTime + datetime.timedelta(0,windowShift*i)
                posture_stack.iloc[i, 1] = posture_stack.iloc[i, 0] + datetime.timedelta(0,epochSize)
                current_epoch_startTime = event_data.Time[(event_data.Time <= posture_stack.iloc[i, 0])].tail(1).item()
                current_epoch_endTime = event_data.Time[(event_data.Time <= posture_stack.iloc[i, 1])].tail(1).item()
                current_epoch = event_data[(event_data.Time >= current_epoch_startTime) & (event_data.Time <= current_epoch_endTime)].copy()
                if len(current_epoch.index) == 1:
                    posture_stack.iloc[i, 2] = current_epoch['ActivityCode (0=sedentary 1=standing 2=stepping 2.1=cycling 3.1=primary lying, 3.2=secondary lying 4=non-wear 5=travelling)']
                else:
                    # if mixed events are required
                    if stack_type == 'mixed':
                        # Crop the time of the first and final events
                        first_new_value = current_epoch['Interval (s)'].iloc[0] - ((posture_stack.iloc[i, 0] - current_epoch_startTime).total_seconds())
                        last_new_value = ((posture_stack.iloc[i, 1] - current_epoch_endTime).total_seconds())
                        current_epoch.iloc[0,2]= first_new_value
                        current_epoch.iloc[-1,2] = last_new_value
                        # Work out which is the predominent event
                        activity_codes = current_epoch['ActivityCode (0=sedentary 1=standing 2=stepping 2.1=cycling 3.1=primary lying, 3.2=secondary lying 4=non-wear 5=travelling)'].unique()
                        activity_codes_counter = {}
                        for code in activity_codes:
                            activity_code_dataframe = current_epoch[current_epoch['ActivityCode (0=sedentary 1=standing 2=stepping 2.1=cycling 3.1=primary lying, 3.2=secondary lying 4=non-wear 5=travelling)'] == code]
                            activity_code_counter_value = activity_code_dataframe['Interval (s)'].sum()
                            activity_codes_counter[code] = activity_code_counter_value
                        max_activity_code = max(activity_codes_counter, key=activity_codes_counter.get)
                        # Assign predominent event as the code
                        posture_stack.iloc[i, 2] = max_activity_code
                    # if pure events are required
                    elif stack_type == 'pure':
                        if np.std(current_epoch['ActivityCode (0=sedentary 1=standing 2=stepping 2.1=cycling 3.1=primary lying, 3.2=secondary lying 4=non-wear 5=travelling)'].unique()) == 0:
                            posture_stack.iloc[i, 2] = current_epoch.iloc[0,3]
                        else:
                            posture_stack.iloc[i, 2] = 99
            self.posture_stack = posture_stack