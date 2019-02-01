protocol "v18.3"
defaults with crc, answer, public

/** \english
	@name Enumerate devices flags
	\endenglish
	\russian
	@name Флаги поиска устройств
	\endrussian
	*/
flagset EnumerateFlags:
ENUMERATE_PROBE		= 0x01	/**< \english Check if a device with OS name name is XIMC device. Be carefuly with this flag because it sends some data to the device.  \endenglish \russian Проверять, является ли устройство XIMC-совместимым. Будте осторожны с этим флагом, т.к. он отправляет данные в устройство.  \endrussian */
ENUMERATE_ALL_COM	= 0x02	/**< \english Check all COM devices \endenglish \russian Проверять все COM-устройства \endrussian */
ENUMERATE_NETWORK	= 0x04	/**< \english Check network devices \endenglish \russian Проверять сетевые устройства \endrussian */

/**
	* \english
	* @name Flags of move state
	* Specify move states.
	* \endenglish
	* \russian
	* @name Флаги состояния движения
	* Возвращаются командой get_status.
	* \endrussian
	* @see get_status
	* @see status_t::move_state
	*/
flagset MoveState:
MOVE_STATE_MOVING		= 0x01	/**< \english This flag indicates that controller is trying to move the motor. Don't use this flag for waiting of completion of the movement command. Use MVCMD_RUNNING flag from the MvCmdSts field instead. \endenglish \russian Если флаг установлен, то контроллер пытается вращать двигателем. Не используйте этот флаг для ожидания завершения команды движения. Вместо него используйте MVCMD_RUNNING из поля MvCmdSts. \endrussian */
MOVE_STATE_TARGET_SPEED	= 0x02	/**< \english Target speed is reached, if flag set. \endenglish \russian Флаг устанавливается при достижении заданной скорости. \endrussian */
MOVE_STATE_ANTIPLAY		= 0x04	/**< \english Motor is playing compensation, if flag set. \endenglish \russian Выполняется компенсация люфта, если флаг установлен. \endrussian */

/**
	* \english
	* @name Flags of internal controller settings
	* \endenglish
	* \russian
	* @name Флаги настроек контроллера
	* \endrussian
	* @see set_controller_name
	* @see get_controller_name
	*/
flagset ControllerFlags:
EEPROM_PRECEDENCE		= 0x01	/**< \english If the flag is set settings from external EEPROM override controller settings. \endenglish \russian Если флаг установлен, то настройки в EEPROM подвижки имеют приоритет над текущими настройками и заменяют их при обнаружении EEPROM. \endrussian */

/**
	* \english
	* @name Flags of power state of stepper motor
	* Specify power states.
	* \endenglish
	* \russian
	* @name Флаги состояния питания шагового мотора
	* Возвращаются командой get_status.
	* \endrussian
	* @see status_t::power_state
	* @see get_status
	*/
flagset PowerState:
PWR_STATE_UNKNOWN	= 0x00	/**< \english Unknown state, should never happen. \endenglish \russian Неизвестное состояние, которое не должно никогда реализовываться. \endrussian */
PWR_STATE_OFF		= 0x01	/**< \english Motor windings are disconnected from the driver. \endenglish \russian Обмотки мотора разомкнуты и не управляются драйвером. \endrussian */
PWR_STATE_NORM		= 0x03	/**< \english Motor windings are powered by nominal current. \endenglish \russian Обмотки запитаны номинальным током. \endrussian */
PWR_STATE_REDUCT	= 0x04	/**< \english Motor windings are powered by reduced current to lower power consumption. \endenglish \russian Обмотки намеренно запитаны уменьшенным током от рабочего для снижения потребляемой мощности. \endrussian */
PWR_STATE_MAX		= 0x05	/**< \english Motor windings are powered by maximum current driver can provide at this voltage. \endenglish \russian Обмотки запитаны максимально доступным током, который может выдать схема при данном напряжении питания. \endrussian */

/**
	* \english
	* @name Status flags
	* Controller flags returned by device query.
	* Contains boolean part of controller state.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги состояния
	* Содержат бинарные значения состояния контроллера. Могут быть объединены с помощью логического ИЛИ.
	* \endrussian
	* @see status_t::flags
	* @see get_status
	*/
flagset StateFlags:
STATE_CONTR						= 0x0000003F	/**< \english Flags of controller states. \endenglish \russian Флаги состояния контроллера. \endrussian */
STATE_ERRC						= 0x00000001	/**< \english Command error encountered. \endenglish \russian Недопустимая команда. \endrussian */
STATE_ERRD						= 0x00000002	/**< \english Data integrity error encountered. \endenglish \russian Нарушение целостности данных. \endrussian */
STATE_ERRV						= 0x00000004	/**< \english Value error encountered. \endenglish \russian Недопустимое значение данных. \endrussian */
STATE_EEPROM_CONNECTED  = 0x00000010	/**< \english EEPROM with settings is connected. \endenglish \russian Подключена память EEPROM с настройками. \endrussian */
STATE_IS_HOMED          = 0x00000020  /**< \english Calibration performed \endenglish \russian Калибровка выполнена \endrussian */
STATE_SECUR						= 0x0073FFC0	/**< \english Flags of security. \endenglish \russian Флаги опасности. \endrussian */
STATE_ALARM						= 0x00000040	/**< \english Controller is in alarm state indicating that something dangerous had happened. Most commands are ignored in this state. To reset the flag a STOP command must be issued. \endenglish \russian Контроллер находится в состоянии ALARM, показывая, что случилась какая-то опасная ситуация. В состоянии ALARM все команды игнорируются пока не будет послана команда STOP и состояние ALARM деактивируется. \endrussian */
STATE_CTP_ERROR					= 0x00000080	/**< \english Control position error(is only used with stepper motor). \endenglish \russian Контроль позиции нарушен(используется только с шаговым двигателем). \endrussian */
STATE_POWER_OVERHEAT			= 0x00000100	/**< \english Power driver overheat. \endenglish \russian Перегрелась силовая часть платы. \endrussian */
STATE_CONTROLLER_OVERHEAT		= 0x00000200	/**< \english Controller overheat. \endenglish \russian Перегрелась микросхема контроллера. \endrussian */
STATE_OVERLOAD_POWER_VOLTAGE	= 0x00000400	/**< \english Power voltage exceeds safe limit. \endenglish \russian Превышено напряжение на силовой части. \endrussian */
STATE_OVERLOAD_POWER_CURRENT	= 0x00000800	/**< \english Power current exceeds safe limit. \endenglish \russian Превышен максимальный ток потребления силовой части. \endrussian */
STATE_OVERLOAD_USB_VOLTAGE		= 0x00001000	/**< \english USB voltage exceeds safe limit. \endenglish \russian Превышено напряжение на USB. \endrussian */
STATE_LOW_USB_VOLTAGE			= 0x00002000	/**< \english USB voltage is insufficient for normal operation. \endenglish \russian Слишком низкое напряжение на USB. \endrussian */
STATE_OVERLOAD_USB_CURRENT		= 0x00004000	/**< \english USB current exceeds safe limit. \endenglish \russian Превышен максимальный ток потребления USB. \endrussian */
STATE_BORDERS_SWAP_MISSET		= 0x00008000	/**< \english Engine stuck at the wrong edge. \endenglish \russian Достижение неверной границы. \endrussian */
STATE_LOW_POWER_VOLTAGE			= 0x00010000	/**< \english Power voltage is lower than Low Voltage Protection limit \endenglish \russian Напряжение на силовой части ниже чем напряжение Low Voltage Protection \endrussian */
STATE_H_BRIDGE_FAULT			= 0x00020000	/**< \english Signal from the driver that fault happened \endenglish \russian Получен сигнал от драйвера о неисправности \endrussian */
STATE_CURRENT_MOTOR_BITS		= 0x000C0000	/**< \english Bits indicating the current operating motor on boards with multiple outputs for engine mounting. \endenglish \russian Биты, показывающие текущий рабочий мотор на платах с несколькими выходами для двигателей. \endrussian */
STATE_CURRENT_MOTOR0			= 0x00000000	/**< \english Motor 0. \endenglish \russian Мотор 0. \endrussian */
STATE_CURRENT_MOTOR1			= 0x00040000	/**< \english Motor 1. \endenglish \russian Мотор 1. \endrussian */
STATE_CURRENT_MOTOR2			= 0x00080000	/**< \english Motor 2. \endenglish \russian Мотор 2. \endrussian */
STATE_CURRENT_MOTOR3			= 0x000C0000	/**< \english Motor 3. \endenglish \russian Мотор 3. \endrussian */
STATE_WINDING_RES_MISMATCH		= 0x00100000	/**< \english The difference between winding resistances is too large \endenglish \russian Сопротивления обмоток отличаются друг от друга слишком сильно \endrussian */
STATE_ENCODER_FAULT 			= 0x00200000	/**< \english Signal from the encoder that fault happened \endenglish \russian Получен сигнал от энкодера о неисправности \endrussian */
STATE_MOTOR_CURRENT_LIMIT		= 0x00400000	/**< \english Current limit exceeded \endenglish \russian Превышен предел по току \endrussian */

/**
	* \english
	* @name Status flags
	* GPIO state flags returned by device query.
	* Contains boolean part of controller state.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги состояния GPIO входов
	* Содержат бинарные значения состояния контроллера. Могут быть объединены с помощью логического ИЛИ.
	* \endrussian
	* @see status_t::flags
	* @see get_status
	*/
flagset GPIOFlags:
STATE_DIG_SIGNAL				= 0x0000FFFF	/**< \english Flags of digital signals. \endenglish \russian Флаги цифровых сигналов. \endrussian */
STATE_RIGHT_EDGE				= 0x00000001	/**< \english Engine stuck at the right edge. \endenglish \russian Достижение правой границы. \endrussian */
STATE_LEFT_EDGE					= 0x00000002	/**< \english Engine stuck at the left edge. \endenglish \russian Достижение левой границы. \endrussian */
STATE_BUTTON_RIGHT				= 0x00000004	/**< \english Button "right" state (1 if pressed). \endenglish \russian Состояние кнопки "вправо" (1, если нажата). \endrussian */
STATE_BUTTON_LEFT				= 0x00000008	/**< \english Button "left" state (1 if pressed). \endenglish \russian Состояние кнопки "влево" (1, если нажата). \endrussian */
STATE_GPIO_PINOUT				= 0x00000010	/**< \english External GPIO works as Out, if flag set; otherwise works as In. \endenglish \russian Если флаг установлен, ввод/вывод общего назначения работает как выход; если флаг сброшен, ввод/вывод работает как вход. \endrussian */
STATE_GPIO_LEVEL				= 0x00000020	/**< \english State of external GPIO pin. \endenglish \russian Состояние ввода/вывода общего назначения. \endrussian */
STATE_BRAKE						= 0x00000200	/**< \english State of Brake pin. \endenglish \russian Состояние вывода управления тормозом(флаг "1" - если на тормоз подаётся питание, "0" - если тормоз не запитан). \endrussian */
STATE_REV_SENSOR				= 0x00000400	/**< \english State of Revolution sensor pin. \endenglish \russian Состояние вывода датчика оборотов(флаг "1", если датчик активен). \endrussian */
STATE_SYNC_INPUT				= 0x00000800	/**< \english State of Sync input pin. \endenglish \russian Состояние входа синхронизации(1, если вход синхронизации активен). \endrussian */
STATE_SYNC_OUTPUT				= 0x00001000	/**< \english State of Sync output pin. \endenglish \russian Состояние выхода синхронизации(1, если выход синхронизации активен). \endrussian */
STATE_ENC_A						= 0x00002000	/**< \english State of encoder A pin. \endenglish \russian Состояние ножки A энкодера(флаг "1", если энкодер активен). \endrussian */
STATE_ENC_B						= 0x00004000	/**< \english State of encoder B pin. \endenglish \russian Состояние ножки B энкодера(флаг "1", если энкодер активен). \endrussian */


/**
	* \english
	* @name Encoder state
	* Encoder state returned by device query.
	* \endenglish
	* \russian
	* @name Состояние энкодера
	* Состояние энкодера, подключенного к контроллеру.
	* \endrussian
	* @see status_t::encsts
	* @see get_status
	*/
flagset EncodeStatus:
ENC_STATE_ABSENT	= 0x00	/**< \english Encoder is absent. \endenglish \russian Энкодер не подключен. \endrussian */
ENC_STATE_UNKNOWN	= 0x01	/**< \english Encoder state is unknown. \endenglish \russian Cостояние энкодера неизвестно. \endrussian */
ENC_STATE_MALFUNC	= 0x02	/**< \english Encoder is connected and malfunctioning. \endenglish \russian Энкодер подключен и неисправен. \endrussian */
ENC_STATE_REVERS	= 0x03	/**< \english Encoder is connected and operational but counts in other direction. \endenglish \russian Энкодер подключен и исправен, но считает в другую сторону. \endrussian */
ENC_STATE_OK		= 0x04	/**< \english Encoder is connected and working properly. \endenglish \russian Энкодер подключен и работает адекватно. \endrussian */

/**
	* \english
	* @name Winding state
	* Motor winding state returned by device query.
	* \endenglish
	* \russian
	* @name Состояние обмоток
	* Состояние обмоток двигателя, подключенного к контроллеру.
	* \endrussian
	* @see status_t::windsts
	* @see get_status
	*/
flagset WindStatus:
WIND_A_STATE_ABSENT		= 0x00	/**< \english Winding A is disconnected. \endenglish \russian Обмотка A не подключена. \endrussian */
WIND_A_STATE_UNKNOWN	= 0x01	/**< \english Winding A state is unknown. \endenglish \russian Cостояние обмотки A неизвестно. \endrussian */
WIND_A_STATE_MALFUNC	= 0x02	/**< \english Winding A is short-circuited. \endenglish \russian Короткое замыкание на обмотке A. \endrussian */
WIND_A_STATE_OK			= 0x03	/**< \english Winding A is connected and working properly. \endenglish \russian Обмотка A работает адекватно. \endrussian */
WIND_B_STATE_ABSENT		= 0x00	/**< \english Winding B is disconnected. \endenglish \russian Обмотка B не подключена. \endrussian */
WIND_B_STATE_UNKNOWN	= 0x10	/**< \english Winding B state is unknown. \endenglish \russian Cостояние обмотки B неизвестно. \endrussian */
WIND_B_STATE_MALFUNC	= 0x20	/**< \english Winding B is short-circuited. \endenglish \russian Короткое замыкание на обмотке B. \endrussian */
WIND_B_STATE_OK			= 0x30	/**< \english Winding B is connected and working properly. \endenglish \russian Обмотка B работает адекватно. \endrussian */

/**
	* \english
	* @name Move command state
	* Move command (command_move, command_movr, command_left, command_right, command_stop, command_home, command_loft, command_sstp)
	* and its state (run, finished, error).
	* \endenglish
	* \russian
	* @name Состояние команды движения
	* Состояние команды движения (касается command_move, command_movr, command_left, command_right, command_stop, command_home, command_loft, command_sstp)
	* и статуса её выполнения (выполяется, завершено, ошибка)
	* \endrussian
	* @see status_t::mvcmdsts
	* @see get_status
	*/
flagset MvcmdStatus:
MVCMD_NAME_BITS	= 0x3F	/**< \english Move command bit mask. \endenglish \russian Битовая маска активной команды. \endrussian */
MVCMD_UKNWN		= 0x00	/**< \english Unknown command. \endenglish \russian Неизвестная команда. \endrussian */
MVCMD_MOVE		= 0x01	/**< \english Command move. \endenglish \russian Команда move. \endrussian */
MVCMD_MOVR		= 0x02	/**< \english Command movr. \endenglish \russian Команда movr. \endrussian */
MVCMD_LEFT		= 0x03	/**< \english Command left. \endenglish \russian Команда left. \endrussian */
MVCMD_RIGHT		= 0x04	/**< \english Command rigt. \endenglish \russian Команда rigt. \endrussian */
MVCMD_STOP		= 0x05	/**< \english Command stop. \endenglish \russian Команда stop. \endrussian */
MVCMD_HOME		= 0x06	/**< \english Command home. \endenglish \russian Команда home. \endrussian */
MVCMD_LOFT		= 0x07	/**< \english Command loft. \endenglish \russian Команда loft. \endrussian */
MVCMD_SSTP		= 0x08	/**< \english Command soft stop. \endenglish \russian Команда плавной остановки(SSTP). \endrussian */
MVCMD_ERROR		= 0x40	/**< \english Finish state (1 - move command have finished with an error, 0 - move command have finished correctly). This flags is actual when MVCMD_RUNNING signals movement finish. \endenglish \russian Состояние завершения движения (1 - команда движения выполнена с ошибкой, 0 - команда движения выполнена корректно). Имеет смысл если MVCMD_RUNNING указывает на завершение движения. \endrussian */
MVCMD_RUNNING	= 0x80	/**< \english Move command state (0 - move command have finished, 1 - move command is being executed). \endenglish \russian Состояние команды движения (0 - команда движения выполнена, 1 - команда движения сейчас выполняется). \endrussian */

/**
	* \english
	* @name Flags of engine settings
	* Specify motor shaft movement algorithm and list of limitations.
	* Flags returned by query of engine settings. May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги параметров мотора
	* Определяют настройки движения и работу ограничителей.
	* Возращаются командой get_engine_settings. Могут быть объединены с помощью логического ИЛИ.
	* \endrussian
	* @see engine_settings_t::flags
	* @see set_engine_settings
	* @see get_engine_settings
	*/
flagset EngineFlags:
ENGINE_REVERSE		= 0x0001	/**< \english Reverse flag. It determines motor shaft rotation direction that corresponds to feedback counts increasing. If not set (default), motor shaft rotation direction under positive voltage corresponds to feedback counts increasing and vice versa. Change it if you see that positive directions on motor and feedback are opposite. \endenglish \russian Флаг реверса. Связывает направление вращения мотора с направлением счета текущей позиции. При сброшенном флаге (по умолчанию) прикладываемое к мотору положительное напряжение увеличивает счетчик позиции. И наоборот, при установленном флаге счетчик позиции увеличивается, когда к мотору приложено отрицательное напряжение. Измените состояние флага, если положительное вращение мотора уменьшает счетчик позиции. \endrussian */
ENGINE_CURRENT_AS_RMS	= 0x0002	/**< \english Engine current meaning flag. If the flag is unset, then engine current value is interpreted as maximum amplitude value. If the flag is set, then engine current value is interpreted as root mean square current value (for stepper) or as the current value calculated from the maximum heat dissipation (bldc). \endenglish \russian Флаг интерпретации значения тока. Если флаг снят, то задаваемое значение тока интерпретируется как максимальная амплитуда тока. Если флаг установлен, то задаваемое значение тока интерпретируется как среднеквадратичное значение тока (для шагового) или как значение тока, посчитанное из максимального тепловыделения (bldc). \endrussian */
ENGINE_MAX_SPEED	= 0x0004	/**< \english Max speed flag. If it is set, engine uses maximum speed achievable with the present engine settings as nominal speed. \endenglish \russian Флаг максимальной скорости. Если флаг установлен, движение происходит на максимальной скорости. \endrussian */
ENGINE_ANTIPLAY		= 0x0008	/**< \english Play compensation flag. If it set, engine makes backlash (play) compensation procedure and reach the predetermined position accurately on low speed. \endenglish \russian Компенсация люфта. Если флаг установлен, позиционер будет подходить к заданной точке всегда с одной стороны. Например, при подходе слева никаких дополнительных действий не совершается, а при подходе справа позиционер проходит целевую позицию на заданное расстояния и возвращается к ней опять же справа. \endrussian */
ENGINE_ACCEL_ON		= 0x0010	/**< \english Acceleration enable flag. If it set, motion begins with acceleration and ends with deceleration. \endenglish \russian Ускорение. Если флаг установлен, движение происходит с ускорением. \endrussian */
ENGINE_LIMIT_VOLT	= 0x0020	/**< \english Maximum motor voltage limit enable flag(is only used with DC motor). \endenglish \russian Номинальное напряжение мотора. Если флаг установлен, напряжение на моторе ограничивается заданным номинальным значением(используется только с DC двигателем). \endrussian */
ENGINE_LIMIT_CURR	= 0x0040	/**< \english Maximum motor current limit enable flag(is only used with DC motor). \endenglish \russian Номинальный ток мотора. Если флаг установлен, ток через мотор ограничивается заданным номинальным значением(используется только с DC двигателем). \endrussian */
ENGINE_LIMIT_RPM	= 0x0080	/**< \english Maximum motor speed limit enable flag. \endenglish \russian Номинальная частота вращения мотора. Если флаг установлен, частота вращения ограничивается заданным номинальным значением. \endrussian */

/**
	* \english
	* @name Flags of microstep mode
	* Specify settings of microstep mode. Using with step motors.
	* Flags returned by query of engine settings. May be combined with bitwise OR
	* \endenglish
	* \russian
	* @name Флаги параметров микрошагового режима
	* Определяют деление шага в микрошаговом режиме. Используются с шаговыми моторами.
	* Возращаются командой get_engine_settings. Могут быть объединены с помощью логического ИЛИ.
	* \endrussian
	* @see engine_settings_t::flags
	* @see set_engine_settings
	* @see get_engine_settings
	*/
flagset MicrostepMode:
MICROSTEP_MODE_FULL		= 0x01	/**< \english Full step mode. \endenglish \russian Полношаговый режим. \endrussian */
MICROSTEP_MODE_FRAC_2	= 0x02	/**< \english 1/2 step mode. \endenglish \russian Деление шага 1/2. \endrussian */
MICROSTEP_MODE_FRAC_4	= 0x03	/**< \english 1/4 step mode. \endenglish \russian Деление шага 1/4. \endrussian */
MICROSTEP_MODE_FRAC_8	= 0x04	/**< \english 1/8 step mode. \endenglish \russian Деление шага 1/8. \endrussian */
MICROSTEP_MODE_FRAC_16	= 0x05	/**< \english 1/16 step mode. \endenglish \russian Деление шага 1/16. \endrussian */
MICROSTEP_MODE_FRAC_32	= 0x06	/**< \english 1/32 step mode. \endenglish \russian Деление шага 1/32. \endrussian */
MICROSTEP_MODE_FRAC_64	= 0x07	/**< \english 1/64 step mode. \endenglish \russian Деление шага 1/64. \endrussian */
MICROSTEP_MODE_FRAC_128	= 0x08	/**< \english 1/128 step mode. \endenglish \russian Деление шага 1/128. \endrussian */
MICROSTEP_MODE_FRAC_256	= 0x09	/**< \english 1/256 step mode. \endenglish \russian Деление шага 1/256. \endrussian */

/**
	* \english
	* @name Flags of engine type
	* Specify motor type.
	* Flags returned by query of engine settings.
	* \endenglish
	* \russian
	* @name Флаги, определяющие тип мотора
	* Определяют тип мотора.
	* Возращаются командой get_entype_settings.
	* \endrussian
	* @see engine_settings_t::flags
	* @see set_entype_settings
	* @see get_entype_settings
	*/
flagset EngineType:
ENGINE_TYPE_NONE		= 0x00	/**< \english A value that shouldn't be used. \endenglish \russian Это значение не нужно использовать. \endrussian */
ENGINE_TYPE_DC			= 0x01	/**< \english DC motor. \endenglish \russian Мотор постоянного тока. \endrussian */
ENGINE_TYPE_2DC			= 0x02	/**< \english 2 DC motors. \endenglish \russian Два мотора постоянного тока, что приводит к эмуляции двух контроллеров. \endrussian */
ENGINE_TYPE_STEP		= 0x03	/**< \english Step motor. \endenglish \russian Шаговый мотор. \endrussian */
ENGINE_TYPE_TEST		= 0x04	/**< \english Duty cycle are fixed. Used only manufacturer. \endenglish \russian Скважность в обмотках фиксирована. Используется только производителем. \endrussian */
ENGINE_TYPE_BRUSHLESS	= 0x05	/**< \english Brushless motor. \endenglish \russian Безщеточный мотор. \endrussian */

/**
	* \english
	* @name Flags of driver type
	* Specify driver type.
	* Flags returned by query of engine settings.
	* \endenglish
	* \russian
	* @name Флаги, определяющие тип силового драйвера
	* Определяют тип силового драйвера.
	* Возращаются командой get_entype_settings.
	* \endrussian
	* @see engine_settings_t::flags
	* @see set_entype_settings
	* @see get_entype_settings
	*/
flagset DriverType:
DRIVER_TYPE_DISCRETE_FET	= 0x01	/**< \english Driver with discrete FET keys. Default option. \endenglish \russian Силовой драйвер на дискретных мосфет-ключах. Используется по умолчанию. \endrussian */
DRIVER_TYPE_INTEGRATE		= 0x02	/**< \english Driver with integrated IC. \endenglish \russian Силовой драйвер с использованием ключей, интегрированных в микросхему. \endrussian */
DRIVER_TYPE_EXTERNAL		= 0x03	/**< \english External driver. \endenglish \russian Внешний силовой драйвер. \endrussian */


/**
	* \english
	* @name Flags of power settings of stepper motor
	* Specify power settings. Flags returned by query of power settings.
	* \endenglish
	* \russian
	* @name Флаги параметров питания шагового мотора
	* Возвращаются командой get_power_settings.
	* \endrussian
	* @see power_settings_t::flags
	* @see get_power_settings
	* @see set_power_settings
	*/
flagset PowerFlags:
POWER_REDUCT_ENABLED	= 0x01	/**< \english Current reduction enabled after CurrReductDelay, if this flag is set. \endenglish \russian Если флаг установлен, уменьшить ток по прошествии CurrReductDelay. Иначе - не уменьшать. \endrussian */
POWER_OFF_ENABLED		= 0x02	/**< \english Power off enabled after PowerOffDelay, if this flag is set. \endenglish \russian Если флаг установлен, снять напряжение с обмоток по прошествии PowerOffDelay. Иначе - не снимать. \endrussian */
POWER_SMOOTH_CURRENT	= 0x04	/**< \english Current ramp-up/down is performed smoothly during current_set_time, if this flag is set. \endenglish \russian Если установлен, то запитывание обмоток, снятие питания или снижение/повышение тока происходят плавно со скоростью CurrentSetTime, а только потом выполняется та задача, которая вызвала это плавное изменение. \endrussian */

/**
	* \english
	* @name Flags of secure settings
	* Specify secure settings. Flags returned by query of secure settings.
	* \endenglish
	* \russian
	* @name Флаги критических параметров.
	* Возвращаются командой get_secure_settings.
	* \endrussian
	* @see secure_settings_t::flags
	* @see get_secure_settings
	* @see set_secure_settings
	*/
flagset SecureFlags:
ALARM_ON_DRIVER_OVERHEATING	= 0x01	/**< \english If this flag is set enter Alarm state on driver overheat signal. \endenglish \russian Если флаг установлен, то войти в состояние Alarm при получении сигнала подступающего перегрева с драйвера. Иначе - игнорировать подступающий перегрев с драйвера. \endrussian */
LOW_UPWR_PROTECTION			= 0x02	/**< \english If this flag is set turn off motor when voltage is lower than LowUpwrOff. \endenglish \russian Если установлен, то выключать силовую часть при напряжении меньшем LowUpwrOff. \endrussian */
H_BRIDGE_ALERT				= 0x04	/**< \english If this flag is set then turn off the power unit with a signal problem in one of the transistor bridge. \endenglish \russian Если установлен, то выключать силовую часть при сигнале неполадки в одном из транзисторных мостов.\endrussian */
ALARM_ON_BORDERS_SWAP_MISSET= 0x08	/**< \english If this flag is set enter Alarm state on borders swap misset \endenglish \russian Если флаг установлен, то войти в состояние Alarm при получении сигнала c противоположного концевика.\endrussian */
ALARM_FLAGS_STICKING		= 0x10	/**< \english If this flag is set only a STOP command can turn all alarms to 0 \endenglish \russian Если флаг установлен, то только по команде STOP возможен сброс всех флагов ALARM.\endrussian */
USB_BREAK_RECONNECT			= 0x20 /**< \english If this flag is set USB brake reconnect module will be enable \endenglish \russian Если флаг установлен, то будет включен блок перезагрузки USB при поломке связи.\endrussian */

/**
	* \english
	* @name Position setting flags
	* Flags used in setting of position.
	* \endenglish
	* \russian
	* @name Флаги установки положения
	* Возвращаются командой get_position.
	* \endrussian
	* @see get_position
	* @see set_position
	*/
flagset PositionFlags:
SETPOS_IGNORE_POSITION	= 0x01	/**< \english Will not reload position in steps/microsteps if this flag is set. \endenglish \russian Если установлен, то позиция в шагах и микрошагах не обновляется. \endrussian */
SETPOS_IGNORE_ENCODER	= 0x02	/**< \english Will not reload encoder state if this flag is set. \endenglish \russian Если установлен, то счётчик энкодера не обновляется. \endrussian */

/**
	* \english
	* @name Feedback type.
	* \endenglish
	* \russian
	* @name Тип обратной связи.
	* \endrussian
	* @see set_feedback_settings
	* @see get_feedback_settings
	*/
flagset FeedbackType:
FEEDBACK_ENCODER		= 0x01	/**< \english Feedback by encoder. \endenglish \russian Обратная связь с помощью энкодера. \endrussian */
FEEDBACK_EMF			= 0x04	/**< \english Feedback by EMF. \endenglish \russian Обратная связь по ЭДС. \endrussian */
FEEDBACK_NONE			= 0x05	/**< \english Feedback is absent. \endenglish \russian Обратная связь отсутствует. \endrussian */

/**
	* \english
	* @name Describes feedback flags.
	* \endenglish
	* \russian
	* @name Флаги обратной связи.
	* \endrussian
	* @see set_feedback_settings
	* @see get_feedback_settings
	*/
flagset FeedbackFlags:
FEEDBACK_ENC_REVERSE	= 0x01	/**< \english Reverse count of encoder. \endenglish \russian Обратный счет у энкодера. \endrussian */
FEEDBACK_ENC_TYPE_BITS	= 0xC0	/**< \english Bits of the encoder type. \endenglish \russian Биты, отвечающие за тип энкодера. \endrussian */
FEEDBACK_ENC_TYPE_AUTO	= 0x00	/**< \english Auto detect encoder type. \endenglish \russian Определять тип энкодера автоматически. \endrussian */
FEEDBACK_ENC_TYPE_SINGLE_ENDED	= 0x40	/**< \english Single ended encoder. \endenglish \russian Недифференциальный энкодер. \endrussian */
FEEDBACK_ENC_TYPE_DIFFERENTIAL	= 0x80	/**< \english Differential encoder. \endenglish \russian Дифференциальный энкодер. \endrussian */

/**
	* \english
	* @name Flags for synchronization input setup
	* \endenglish
	* \russian
	* @name Флаги настроек синхронизации входа
	* \endrussian
	* @see sync_settings_t::syncin_flags
	* @see get_sync_settings
	* @see set_sync_settings
	*/
flagset SyncInFlags:
SYNCIN_ENABLED		= 0x01	/**< \english Synchronization in mode is enabled, if this flag is set. \endenglish \russian Включение необходимости импульса синхронизации для начала движения. \endrussian */
SYNCIN_INVERT		= 0x02	/**< \english Trigger on falling edge if flag is set, on rising edge otherwise. \endenglish \russian Если установлен - срабатывает по переходу из 1 в 0. Иначе - из 0 в 1. \endrussian */
SYNCIN_GOTOPOSITION	= 0x04	/**< \english The engine is go to position specified in Position and uPosition, if this flag is set. And it is shift on the Position and uPosition, if this flag is unset \endenglish \russian Если флаг установлен, то двигатель смещается к позиции, установленной в Position и uPosition, иначе двигатель смещается на Position и uPosition \endrussian */

/**
	* \english
	* @name Flags of synchronization output
	* \endenglish
	* \russian
	* @name Флаги настроек синхронизации выхода
	* \endrussian
	* @see sync_settings_t::syncout_flags
	* @see get_sync_settings
	* @see set_sync_settings
	*/
flagset SyncOutFlags:
SYNCOUT_ENABLED		= 0x01	/**< \english Synchronization out pin follows the synchronization logic, if set. It governed by SYNCOUT_STATE flag otherwise. \endenglish \russian Синхронизация выхода работает согласно настройкам, если флаг установлен. В ином случае значение выхода фиксировано и подчиняется SYNCOUT_STATE. \endrussian */
SYNCOUT_STATE		= 0x02	/**< \english When output state is fixed by negative SYNCOUT_ENABLED flag, the pin state is in accordance with this flag state. \endenglish \russian Когда значение выхода управляется напрямую (см. флаг SYNCOUT_ENABLED), значение на выходе соответствует значению этого флага. \endrussian */
SYNCOUT_INVERT		= 0x04	/**< \english Low level is active, if set, and high level is active otherwise. \endenglish \russian Нулевой логический уровень является активным, если флаг установлен, а единичный - если флаг сброшен. \endrussian */
SYNCOUT_IN_STEPS	= 0x08	/**< \english Use motor steps/encoder pulses instead of milliseconds for output pulse generation if the flag is set. \endenglish \russian Если флаг установлен использовать шаги/импульсы энкодера для выходных импульсов синхронизации вместо миллисекунд. \endrussian */
SYNCOUT_ONSTART		= 0x10	/**< \english Generate synchronization pulse when movement starts. \endenglish \russian Генерация синхронизирующего импульса при начале движения. \endrussian */
SYNCOUT_ONSTOP		= 0x20	/**< \english Generate synchronization pulse when movement stops. \endenglish \russian Генерация синхронизирующего импульса при остановке. \endrussian */
SYNCOUT_ONPERIOD	= 0x40	/**< \english Generate synchronization pulse every SyncOutPeriod encoder pulses. \endenglish \russian Выдать импульс синхронизации после прохождения SyncOutPeriod отсчётов. \endrussian */

/**
	* \english
	* @name External IO setup flags
	* \endenglish
	* \russian
	* @name Флаги настройки работы внешнего ввода/вывода
	* \endrussian
	* @see extio_settings_t::setup_flags
	* @see get_extio_settings
	* @see set_extio_settings
	*/
flagset ExtioSetupFlags:
EXTIO_SETUP_OUTPUT	= 0x01	/**< \english EXTIO works as output if flag is set, works as input otherwise. \endenglish \russian Если флаг установлен, то ножка в состоянии вывода, иначе - ввода. \endrussian */
EXTIO_SETUP_INVERT	= 0x02	/**< \english Interpret EXTIO states and fronts inverted if flag is set. Falling front as input event and low logic level as active state. \endenglish \russian Eсли флаг установлен, то нули считаются активным состоянием выхода, а спадающие фронты как момент подачи входного сигнала. \endrussian */

/**
	* \english
	* @name External IO mode flags
	* \endenglish
	* \russian
	* @name Флаги настройки режимов внешнего ввода/вывода
	* \endrussian
	* @see extio_settings_t::extio_mode_flags
	* @see get_extio_settings
	* @see set_extio_settings
	*/
flagset ExtioModeFlags:
EXTIO_SETUP_MODE_IN_BITS            = 0x0F  /**< \english Bits of the behaviour selector when the signal on input goes to the active state. \endenglish \russian Биты, отвечающие за поведение при переходе сигнала в активное состояние. \endrussian */
EXTIO_SETUP_MODE_IN_NOP             = 0x00  /**< \english Do nothing. \endenglish \russian Ничего не делать. \endrussian */
EXTIO_SETUP_MODE_IN_STOP            = 0x01  /**< \english Issue STOP command, ceasing the engine movement. \endenglish \russian По переднему фронту входного сигнала делается остановка двигателя (эквивалент команды STOP). \endrussian */
EXTIO_SETUP_MODE_IN_PWOF            = 0x02  /**< \english Issue PWOF command, powering off all engine windings. \endenglish \russian Выполняет команду PWOF, обесточивая обмотки двигателя. \endrussian */
EXTIO_SETUP_MODE_IN_MOVR            = 0x03  /**< \english Issue MOVR command with last used settings. \endenglish \russian Выполняется команда MOVR с последними настройками. \endrussian */
EXTIO_SETUP_MODE_IN_HOME            = 0x04  /**< \english Issue HOME command. \endenglish \russian Выполняется команда HOME. \endrussian */
EXTIO_SETUP_MODE_IN_ALARM           = 0x05  /**< \english Set Alarm when the signal goes to the active state. \endenglish \russian Войти в состояние ALARM при переходе сигнала в активное состояние. \endrussian */
EXTIO_SETUP_MODE_OUT_BITS           = 0xF0  /**< \english Bits of the output behaviour selection. \endenglish \russian Биты выбора поведения на выходе. \endrussian */
EXTIO_SETUP_MODE_OUT_OFF            = 0x00  /**< \english EXTIO pin always set in inactive state. \endenglish \russian Ножка всегда в неактивном состоянии. \endrussian */
EXTIO_SETUP_MODE_OUT_ON             = 0x10  /**< \english EXTIO pin always set in active state. \endenglish \russian Ножка всегда в активном состоянии. \endrussian */
EXTIO_SETUP_MODE_OUT_MOVING         = 0x20  /**< \english EXTIO pin stays active during moving state. \endenglish \russian Ножка находится в активном состоянии при движении. \endrussian */
EXTIO_SETUP_MODE_OUT_ALARM          = 0x30  /**< \english EXTIO pin stays active during Alarm state. \endenglish \russian Ножка находится в активном состоянии при нахождении в состоянии ALARM. \endrussian */
EXTIO_SETUP_MODE_OUT_MOTOR_ON       = 0x40  /**< \english EXTIO pin stays active when windings are powered. \endenglish \russian Ножка находится в активном состоянии при подаче питания на обмотки. \endrussian */
EXTIO_SETUP_MODE_OUT_MOTOR_FOUND    = 0x50  /**< \english EXTIO pin stays active when motor is connected (first winding). \endenglish \russian Ножка находится в активном состоянии при обнаружении подключенного двигателя (первой обмотки). \endrussian */

/**
	* \english
	* @name Border flags
	* Specify types of borders and motor behaviour on borders.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги границ
	* Типы границ и поведение позиционера на границах.
	* Могут быть объединены с помощью побитового ИЛИ.
	* \endrussian
	* @see get_edges_settings
	* @see set_edges_settings
	*/
flagset BorderFlags:
BORDER_IS_ENCODER				= 0x01	/**< \english Borders are fixed by predetermined encoder values, if set; borders position on limit switches, if not set. \endenglish \russian Если флаг установлен, границы определяются предустановленными точками на шкале позиции. Если флаг сброшен, границы определяются концевыми выключателями. \endrussian */
BORDER_STOP_LEFT				= 0x02	/**< \english Motor should stop on left border. \endenglish \russian Если флаг установлен, мотор останавливается при достижении левой границы. \endrussian */
BORDER_STOP_RIGHT				= 0x04	/**< \english Motor should stop on right border. \endenglish \russian Если флаг установлен, мотор останавливается при достижении правой границы. \endrussian */
BORDERS_SWAP_MISSET_DETECTION	= 0x08	/**< \english Motor should stop on both borders. Need to save motor then wrong border settings is set\endenglish \russian Если флаг установлен, мотор останавливается при достижении обоих границ. Нужен для предотвращения поломки двигателя при неправильных настройках концевиков \endrussian */

/**
	* \english
	* @name Limit switches flags
	* Specify electrical behaviour of limit switches like order and pulled positions.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги концевых выключателей
	* Определяют направление и состояние границ.
	* Могут быть объединены с помощью побитового ИЛИ.
	* \endrussian
	* @see get_edges_settings
	* @see set_edges_settings
	*/
flagset EnderFlags:
ENDER_SWAP				= 0x01	/**< \english First limit switch on the right side, if set; otherwise on the left side. \endenglish \russian Если флаг установлен, первый концевой выключатель находится справа; иначе - слева. \endrussian */
ENDER_SW1_ACTIVE_LOW	= 0x02	/**< \english 1 - Limit switch connnected to pin SW1 is triggered by a low level on pin. \endenglish \russian 1 - Концевик, подключенный к ножке SW1, считается сработавшим по низкому уровню на контакте. \endrussian */
ENDER_SW2_ACTIVE_LOW	= 0x04	/**< \english 1 - Limit switch connnected to pin SW2 is triggered by a low level on pin. \endenglish \russian 1 - Концевик, подключенный к ножке SW2, считается сработавшим по низкому уровню на контакте. \endrussian */

/**
	* \english
	* @name Brake settings flags
	* Specify behaviour of brake.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги настроек тормоза
	* Определяют поведение тормоза.
	* Могут быть объединены с помощью побитового ИЛИ.
	* \endrussian
	* @see get_brake_settings
	* @see set_brake_settings
	*/
flagset BrakeFlags:
BRAKE_ENABLED			= 0x01	/**< \english Brake control is enabled, if this flag is set. \endenglish \russian Управление тормозом включено, если флаг установлен. \endrussian */
BRAKE_ENG_PWROFF		= 0x02	/**< \english Brake turns off power of step motor, if this flag is set. \endenglish \russian Тормоз отключает питание шагового мотора, если флаг установлен. \endrussian */

/**
	* \english
	* @name Control flags
	* Specify motor control settings by joystick or buttons.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги управления
	* Определяют параметры управления мотором с помощью джойстика или кнопок.
	* Могут быть объединены с помощью побитового ИЛИ.
	* \endrussian
	* @see get_control_settings
	* @see set_control_settings
	*/
flagset ControlFlags:
CONTROL_MODE_BITS				= 0x03	/**< \english Bits to control engine by joystick or buttons. \endenglish \russian Биты управления мотором с помощью джойстика или кнопок влево/вправо. \endrussian */
CONTROL_MODE_OFF				= 0x00	/**< \english Control is disabled. \endenglish \russian Управление отключено. \endrussian */
CONTROL_MODE_JOY				= 0x01	/**< \english Control by joystick. \endenglish \russian Управление с помощью джойстика. \endrussian */
CONTROL_MODE_LR					= 0x02	/**< \english Control by left/right buttons. \endenglish \russian Управление с помощью кнопок left/right. \endrussian */
CONTROL_BTN_LEFT_PUSHED_OPEN	= 0x04	/**< \english Pushed left button corresponds to open contact, if this flag is set. \endenglish \russian Левая кнопка нормально разомкнутая, если флаг установлен. \endrussian */
CONTROL_BTN_RIGHT_PUSHED_OPEN	= 0x08	/**< \english Pushed right button corresponds to open contact, if this flag is set. \endenglish \russian Правая кнопка нормально разомкнутая, если флаг установлен. \endrussian */

/**
	* \english
	* @name Joystick flags
	* Control joystick states.
	* \endenglish
	* \russian
	* @name Флаги джойстика
	* Управляют состояниями джойстика.
	* \endrussian
	* @see set_joystick_settings
	* @see get_joystick_settings
	*/
flagset JoyFlags:
JOY_REVERSE				= 0x01	/**< \english Joystick action is reversed. Joystick deviation to the upper values correspond to negative speeds and vice versa. \endenglish \russian Реверс воздействия джойстика. Отклонение джойстика к большим значениям приводит к отрицательной скорости и наоборот. \endrussian */

/**
	* \english
	* @name Position control flags
	* Specify settings of position control.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги контроля позиции
	* Определяют настройки контроля позиции.
	* Могут быть объединены с помощью побитового ИЛИ.
	* \endrussian
	* @see get_ctp_settings
	* @see set_ctp_settings
	*/
flagset CtpFlags:
CTP_ENABLED			    = 0x01	/**< \english Position control is enabled, if flag set. \endenglish \russian Контроль позиции включен, если флаг установлен. \endrussian */
CTP_BASE			    = 0x02	/**< \english Position control is based on revolution sensor, if this flag is set; otherwise it is based on encoder. \endenglish \russian Опорой является датчик оборотов, если флаг установлен; иначе - энкодер. \endrussian */
CTP_ALARM_ON_ERROR	    = 0x04	/**< \english Set ALARM on mismatch, if flag set. \endenglish \russian Войти в состояние ALARM при расхождении позиции, если флаг установлен. \endrussian */
REV_SENS_INV	        = 0x08	/**< \english Sensor is active when it 0 and invert makes active level 1. That is, if you do not invert, it is normal logic - 0 is the activation. \endenglish \russian Сенсор считается активным, когда на нём 0, а инвертирование делает активным уровнем 1. То есть если не инвертировать, то действует обычная логика - 0 это срабатывание/активация/активное состояние. \endrussian */
CTP_ERROR_CORRECTION    = 0x10 /**< \english Correct errors which appear when slippage if the flag is set. It works only with the encoder. Incompatible with flag CTP_ALARM_ON_ERROR. \endenglish \russian Корректировать ошибки, возникающие при проскальзывании, если флаг установлен. Работает только с энкодером. Несовместимо с флагом CTP_ALARM_ON_ERROR.\endrussian */

/**
	* \english
	* @name Home settings flags
	* Specify behaviour for home command.
	* May be combined with bitwise OR.
	* \endenglish
	* \russian
	* @name Флаги настроек команды home
	* Определяют поведение для команды home.
	* Могут быть объединены с помощью побитового ИЛИ.
	* \endrussian
	* @see get_home_setting	s
	* @see set_home_settings
	* @see command_home
	*/
flagset HomeFlags:
HOME_DIR_FIRST			= 0x0001	/**< \english Flag defines direction of 1st motion after execution of home command. Direction is right, if set; otherwise left. \endenglish \russian Определяет направление первоначального движения мотора после поступления команды HOME. Если флаг установлен - вправо; иначе - влево. \endrussian */
HOME_DIR_SECOND			= 0x0002	/**< \english Flag defines direction of 2nd motion. Direction is right, if set; otherwise left. \endenglish \russian Определяет направление второго движения мотора. Если флаг установлен - вправо; иначе - влево. \endrussian */
HOME_MV_SEC_EN			= 0x0004	/**< \english Use the second phase of calibration to the home position, if set; otherwise the second phase is skipped. \endenglish \russian Если флаг установлен, реализуется второй этап доводки в домашнюю позицию; иначе - этап пропускается. \endrussian */
HOME_HALF_MV			= 0x0008	/**< \english If the flag is set, the stop signals are ignored in start of second movement the first half-turn. \endenglish \russian Если флаг установлен, в начале второго движения первые пол оборота сигналы завершения движения игнорируются. \endrussian */
HOME_STOP_FIRST_BITS	= 0x0030	/**< \english Bits of the first stop selector. \endenglish \russian Биты, отвечающие за выбор сигнала завершения первого движения. \endrussian */
HOME_STOP_FIRST_REV		= 0x0010	/**< \english First motion stops by  revolution sensor. \endenglish \russian Первое движение завершается по сигналу с Revolution sensor. \endrussian */
HOME_STOP_FIRST_SYN		= 0x0020	/**< \english First motion stops by synchronization input. \endenglish \russian Первое движение завершается по сигналу со входа синхронизации. \endrussian */
HOME_STOP_FIRST_LIM		= 0x0030	/**< \english First motion stops by limit switch. \endenglish \russian Первое движение завершается по сигналу с концевика. \endrussian */
HOME_STOP_SECOND_BITS	= 0x00C0	/**< \english Bits of the second stop selector. \endenglish \russian Биты, отвечающие за выбор сигнала завершения второго движения. \endrussian */
HOME_STOP_SECOND_REV	= 0x0040	/**< \english Second motion stops by  revolution sensor. \endenglish \russian Второе движение завершается по сигналу с Revolution sensor. \endrussian */
HOME_STOP_SECOND_SYN	= 0x0080	/**< \english Second motion stops by synchronization input. \endenglish \russian Второе движение завершается по сигналу со входа синхронизации. \endrussian */
HOME_STOP_SECOND_LIM	= 0x00C0	/**< \english Second motion stops by limit switch. \endenglish \russian Второе движение завершается по сигналу с концевика. \endrussian */
HOME_USE_FAST           = 0x0100	/**< \english Use the fast algorithm of calibration to the home position, if set; otherwise the traditional algorithm. \endenglish \russian Если флаг установлен, используется быстрый поиск домашней позиции; иначе - традиционный. \endrussian */

/**
	* \english
	* @name UART parity flags
	* \endenglish
	* \russian
	* @name Флаги настроек четности команды uart
	* \endrussian
	*/
flagset UARTSetupFlags:
UART_PARITY_BITS		= 0x03	/**< \english Bits of the parity. \endenglish \russian Биты, отвечающие за выбор четности. \endrussian */
UART_PARITY_BIT_EVEN	= 0x00	/**< \english Parity bit 1, if  even \endenglish \russian Бит 1, если чет \endrussian */
UART_PARITY_BIT_ODD		= 0x01	/**< \english Parity bit 1, if  odd \endenglish \russian Бит 1, если нечет \endrussian */
UART_PARITY_BIT_SPACE	= 0x02	/**< \english Parity bit always 0 \endenglish \russian Бит четности всегда 0 \endrussian */
UART_PARITY_BIT_MARK	= 0x03	/**< \english Parity bit always 1 \endenglish \russian Бит четности всегда 1 \endrussian */
UART_PARITY_BIT_USE		= 0x04	/**< \english None parity \endenglish \russian Бит чётности не используется, если "0"; бит четности используется, если "1" \endrussian */
UART_STOP_BIT			= 0x08	/**< \english If set - one stop bit, else two stop bit \endenglish \russian Если установлен, один стоповый бит; иначе - 2 стоповых бита \endrussian */

/** 
 	* \english
	* @name Motor Type flags
	* \endenglish
	* \russian
	* @name Флаг типа двигателя
	* \endrussian
	*/
flagset MotorTypeFlags:
MOTOR_TYPE_UNKNOWN		= 0x00	/**< \english Unknown type of engine \endenglish \russian Неизвестный двигатель \endrussian */
MOTOR_TYPE_STEP			= 0x01	/**< \english Step engine \endenglish \russian Шаговый двигатель \endrussian */
MOTOR_TYPE_DC			= 0x02	/**< \english DC engine \endenglish \russian DC двигатель \endrussian */
MOTOR_TYPE_BLDC			= 0x03	/**< \english BLDC engine \endenglish \russian BLDC двигатель \endrussian */

/** 
 	* \english
	* @name Encoder settings flags
	* \endenglish
	* \russian
	* @name Флаги настроек энкодера
	* \endrussian
	*/
flagset EncoderSettingsFlags:
ENCSET_DIFFERENTIAL_OUTPUT			= 0x0001	/**< \english If flag is set the encoder has differential output, else single ended output \endenglish \russian Если флаг установлен, то энкодер имеет дифференциальный выход, иначе - несимметричный выход \endrussian */
ENCSET_PUSHPULL_OUTPUT				= 0x0004	/**< \english If flag is set the encoder has push-pull output, else open drain output \endenglish \russian Если флаг установлен, то энкодер имеет двухтактный выход, иначе - выход с открытым коллектором \endrussian */
ENCSET_INDEXCHANNEL_PRESENT 		= 0x0010	/**< \english If flag is set the encoder has index channel, else encoder hasn`t it \endenglish \russian Если флаг установлен, то энкодер имеет дополнительный индексный канал, иначе - он отсутствует \endrussian */
ENCSET_REVOLUTIONSENSOR_PRESENT 	= 0x0040	/**< \english If flag is set the encoder has revolution sensor, else encoder hasn`t it \endenglish \russian Если флаг установлен, то энкодер имеет датчик оборотов, иначе - он отсутствует \endrussian */
ENCSET_REVOLUTIONSENSOR_ACTIVE_HIGH = 0x0100	/**< \english If flag is set the revolution sensor active state is high logic state, else active state is low logic state \endenglish \russian Если флаг установлен, то активное состояние датчика оборотов соответствует логической 1, иначе - логическому 0 \endrussian */

/** 
 	* \english
	* @name Magnetic brake settings flags
	* \endenglish
	* \russian
	* @name Флаги настроек энкодера
	* \endrussian
	*/
flagset MBSettingsFlags:
MB_AVAILABLE					= 0x01	/**< \english If flag is set the magnetic brake is available \endenglish \russian Если флаг установлен, то магнитный тормоз доступен \endrussian */
MB_POWERED_HOLD					= 0x02	/**< \english If this flag is set the magnetic brake is on when powered \endenglish \russian Если флаг установлен, то магнитный тормоз находится в режиме удержания (активен) при подаче питания \endrussian */

/** 
 	* \english
	* @name Temperature sensor settings flags
	* \endenglish
	* \russian
	* @name Флаги настроек температурного датчика
	* \endrussian
	*/
flagset TSSettingsFlags:
TS_TYPE_BITS					= 0x07	/**< \english Bits of the temperature sensor type \endenglish \russian Биты, отвечающие за тип температурного датчика. \endrussian */
TS_TYPE_UNKNOWN					= 0x00	/**< \english Unknow type of sensor \endenglish \russian Неизвестный сенсор \endrussian */
TS_TYPE_THERMOCOUPLE			= 0x01	/**< \english Thermocouple \endenglish \russian Термопара \endrussian */
TS_TYPE_SEMICONDUCTOR			= 0x02	/**< \english The semiconductor temperature sensor \endenglish \russian Полупроводниковый температурный датчик \endrussian */
TS_AVAILABLE					= 0x08	/**< \english If flag is set the temperature sensor is available \endenglish \russian Если флаг установлен, то датчик температуры доступен \endrussian */

/** 
 	* \english
	* @name Temperature sensor settings flags
	* \endenglish
	* \russian
	* @name Флаги настроек температурного датчика
	* \endrussian
	*/
flagset LSFlags:
LS_ON_SW1_AVAILABLE				= 0x01	/**< \english If flag is set the limit switch connnected to pin SW1 is available \endenglish \russian Если флаг установлен, то концевик, подключенный к ножке SW1, доступен \endrussian */
LS_ON_SW2_AVAILABLE				= 0x02	/**< \english If flag is set the limit switch connnected to pin SW2 is available \endenglish \russian Если флаг установлен, то концевик, подключенный к ножке SW2, доступен \endrussian */
LS_SW1_ACTIVE_LOW				= 0x04	/**< \english If flag is set the limit switch connnected to pin SW1 is triggered by a low level on pin \endenglish \russian Если флаг установлен, то концевик, подключенный к ножке SW1, считается сработавшим по низкому уровню на контакте \endrussian */
LS_SW2_ACTIVE_LOW				= 0x08	/**< \english If flag is set the limit switch connnected to pin SW2 is triggered by a low level on pin \endenglish \russian Если флаг установлен, то концевик, подключенный к ножке SW2, считается сработавшим по низкому уровню на контакте \endrussian */
LS_SHORTED						= 0x10	/**< \english If flag is set the Limit switches is shorted \endenglish \russian Если флаг установлен, то концевики закорочены. \endrussian */

/**
	* \english
	* @name Controller settings setup
	* Functions for adjusting engine read/write almost all controller settings.
	* \endenglish
	* \russian
	* @name Группа команд настройки контроллера
	* Функции для чтения/записи большинства настроек контроллера.
	* \endrussian
	*/

//@{

/** $XIR
	* \english
	* Feedback settings.
	* @param id an identifier of device
	* @param[out] IPS number of encoder counts per shaft revolution. Range: 1..65535. The field is obsolete, it is recommended to write 0 to IPS and use the extended CountsPerTurn field. You may need to update the controller firmware to the latest version.
	* @param[out] FeedbackType type of feedback
	* @param[out] FeedbackFlags flags of feedback
	* @param[out] CountsPerTurn number of encoder counts per shaft revolution. Range: 1..4294967295. To use the CountsPerTurn field, write 0 in the IPS field, otherwise the value from the IPS field will be used.
	* \endenglish
	* \russian
	* Чтение настроек обратной связи
	* @param id идентификатор устройства
	* @param[out] IPS количество отсчётов энкодера на оборот вала. Диапазон: 1..65535. Поле устарело, рекомендуется записывать 0 в IPS и использовать расширенное поле CountsPerTurn. Может потребоваться обновление микропрограммы контроллера до последней версии.
	* @param[out] FeedbackType тип обратной связи
	* @param[out] FeedbackFlags флаги обратной связи
	* @param[out] CountsPerTurn количество отсчётов энкодера на оборот вала. Диапазон: 1..4294967295. Для использования поля CountsPerTurn нужно записать 0 в поле IPS, иначе будет использоваться значение из поля IPS.
	* \endrussian
	*/
/** $XIW
	* \english
	* Feedback settings.
	* @param id an identifier of device
	* @param[in] IPS number of encoder counts per shaft revolution. Range: 1..65535. The field is obsolete, it is recommended to write 0 to IPS and use the extended CountsPerTurn field. You may need to update the controller firmware to the latest version.
	* @param[in] FeedbackType type of feedback
	* @param[in] FeedbackFlags flags of feedback
	* @param[in] CountsPerTurn number of encoder counts per shaft revolution. Range: 1..4294967295. To use the CountsPerTurn field, write 0 in the IPS field, otherwise the value from the IPS field will be used.
	* \endenglish
	* \russian
	* Запись настроек обратной связи.
	* @param id идентификатор устройства
	* @param[in] IPS количество отсчётов энкодера на оборот вала. Диапазон: 1..65535. Поле устарело, рекомендуется записывать 0 в IPS и использовать расширенное поле CountsPerTurn. Может потребоваться обновление микропрограммы контроллера до последней версии.
	* @param[in] FeedbackType тип обратной связи
	* @param[in] FeedbackFlags флаги обратной связи
	* @param[in] CountsPerTurn количество отсчётов энкодера на оборот вала. Диапазон: 1..4294967295. Для использования поля CountsPerTurn нужно записать 0 в поле IPS, иначе будет использоваться значение из поля IPS.
	* \endrussian
	*/
/** $XIS
	* \english
	* Feedback settings.
	* This structure contains feedback settings.
	* \endenglish
	* \russian
	* Настройки обратной связи.
	* Эта структура содержит настройки обратной связи.
	* \endrussian
	*/
command "feedback_settings" universal "fbs" (18)
fields:
    int16u IPS                                  /**< \english The number of encoder counts per shaft revolution. Range: 1..655535. The field is obsolete, it is recommended to write 0 to IPS and use the extended CountsPerTurn field. You may need to update the controller firmware to the latest version. \endenglish \russian Количество отсчётов энкодера на оборот вала. Диапазон: 1..65535. Поле устарело, рекомендуется записывать 0 в IPS и использовать расширенное поле CountsPerTurn. Может потребоваться обновление микропрограммы контроллера до последней версии. \endrussian */
    int8u flag FeedbackType of FeedbackType     /**< \english Type of feedback \endenglish \russian Тип обратной связи \endrussian */
    int8u flag FeedbackFlags of FeedbackFlags   /**< \english Flags \endenglish \russian Флаги \endrussian */
    int32u CountsPerTurn                        /**< \english The number of encoder counts per shaft revolution. Range: 1..4294967295. To use the CountsPerTurn field, write 0 in the IPS field, otherwise the value from the IPS field will be used. \endenglish \russian Количество отсчётов энкодера на оборот вала. Диапазон: 1..4294967295. Для использования поля CountsPerTurn нужно записать 0 в поле IPS, иначе будет использоваться значение из поля IPS. \endrussian */
    reserved 4

/** $XIR
	* \english
	* Read home settings.
	* This function fill structure with settings of calibrating position.
	* @see home_settings_t
	* @param id an identifier of device
	* @param[out] home_settings calibrating position settings
	* \endenglish
	* \russian
	* Команда чтения настроек для подхода в home position.
	* Эта функция заполняет структуру настроек, использующихся для калибровки позиции, в память контроллера.
	* @see home_settings_t
	* @param id идентификатор устройства
	* @param[out] home_settings настройки калибровки позиции
	* \endrussian
	*/
/** $XIW
	* \english
	* Set home settings.
	* This function send structure with calibrating position settings to controller's memory.
	* @see home_settings_t
	* @param id an identifier of device
	* @param[in] home_settings calibrating position settings
	* \endenglish
	* \russian
	* Команда записи настроек для подхода в home position.
	* Эта функция записывает структуру настроек, использующихся для калибровки позиции, в память контроллера.
	* @see home_settings_t
	* @param id идентификатор устройства
	* @param[out] home_settings настройки калибровки позиции
	* \endrussian
	*/
/** $XIS
	* \english
	* Position calibration settings.
	* This structure contains settings used in position calibrating.
	* It specify behaviour of calibrating position.
	* \endenglish
	* \russian
	* Настройки калибровки позиции.
	* Эта структура содержит настройки, использующиеся при калибровке позиции.
	* \endrussian
	* @see get_home_settings
	* @see set_home_settings
	* @see command_home
	*/
command "home_settings" universal "hom" (33)
fields:
	calb float FastHome					/**< \english Speed used for first motion. \endenglish \russian Скорость первого движения. \endrussian */
	normal int32u FastHome				/**< \english Speed used for first motion. Range: 0..100000. \endenglish \russian Скорость первого движения. Диапазон: 0..100000 \endrussian */
	normal int8u uFastHome				/**< \english Part of the speed for first motion, microsteps. \endenglish \russian Дробная часть скорости первого движения в микрошагах(используется только с шаговым двигателем). \endrussian */
	calb float SlowHome					/**< \english Speed used for second motion. \endenglish \russian Скорость второго движения. \endrussian */
	normal int32u SlowHome				/**< \english Speed used for second motion. Range: 0..100000. \endenglish \russian Скорость второго движения. Диапазон: 0..100000. \endrussian */
	normal int8u uSlowHome				/**< \english Part of the speed for second motion, microsteps. \endenglish \russian Дробная часть скорости второго движения в микрошагах(используется только с шаговым двигателем). \endrussian */
	calb float HomeDelta				/**< \english Distance from break point. \endenglish \russian Расстояние отхода от точки останова. \endrussian */
	normal int32s HomeDelta				/**< \english Distance from break point. \endenglish \russian Расстояние отхода от точки останова. \endrussian */
	normal int16s uHomeDelta			/**< \english Part of the delta distance, microsteps. Range: -255..255. \endenglish \russian Дробная часть расстояния отхода от точки останова в микрошагах(используется только с шаговым двигателем). Диапазон: -255..255. \endrussian */
	int16u flag HomeFlags of HomeFlags	/**< \english Set of flags specify direction and stopping conditions. \endenglish \russian Набор флагов, определяющие такие параметры, как направление и условия останова. \endrussian */
	reserved 9

/** $XIR
	* \english
	* Read command setup movement (speed, acceleration, threshold and etc).
	* @param id an identifier of device
	* @param[out] move_settings structure contains move settings: speed, acceleration, deceleration etc.
	* \endenglish
	* \russian
	* Команда чтения настроек перемещения (скорость, ускорение, threshold и скорость в режиме антилюфта).
	* @param id идентификатор устройства
	* @param[out] move_settings структура, содержащая настройки движения: скорость, ускорение, и т.д.
	* \endrussian
	*/
/** $XIW
	* \english
	* Set command setup movement (speed, acceleration, threshold and etc).
	* @param id an identifier of device
	* @param[in] move_settings structure contains move settings: speed, acceleration, deceleration etc.
	* \endenglish
	* \russian
	* Команда записи настроек перемещения (скорость, ускорение, threshold и скорость в режиме антилюфта).
	* @param id идентификатор устройства
	* @param[in] move_settings структура, содержащая настройки движения: скорость, ускорение, и т.д.
	* \endrussian
	*/
/** $XIS
	* \english
	* Move settings.
	* \endenglish
	* \russian
	* Настройки движения.
	* \endrussian
	* @see set_move_settings
	* @see get_move_settings
	*/
command "move_settings" universal "mov" (30)
fields:
	calb float Speed			/**< \english Target speed. \endenglish \russian Заданная скорость. \endrussian */
	normal int32u Speed			/**< \english Target speed (for stepper motor: steps/s, for DC: rpm). Range: 0..100000. \endenglish \russian Заданная скорость (для ШД: шагов/c, для DC: rpm). Диапазон: 0..100000. \endrussian */
	normal int8u uSpeed			/**< \english Target speed in microstep fractions/s. Using with stepper motor only. \endenglish \russian Заданная скорость в единицах деления микрошага в секунду. Используется только с шаговым мотором. \endrussian */
	calb float Accel			/**< \english Motor shaft acceleration, steps/s^2(stepper motor) or RPM/s(DC). \endenglish \russian Ускорение, заданное в шагах в секунду^2(ШД) или в оборотах в минуту за секунду(DC). \endrussian */
	normal int16u Accel			/**< \english Motor shaft acceleration, steps/s^2(stepper motor) or RPM/s(DC). Range: 1..65535. \endenglish \russian Ускорение, заданное в шагах в секунду^2(ШД) или в оборотах в минуту за секунду(DC). Диапазон: 1..65535. \endrussian */
	calb float Decel			/**< \english Motor shaft deceleration, steps/s^2(stepper motor) or RPM/s(DC). \endenglish \russian Торможение, заданное в шагах в секунду^2(ШД) или в оборотах в минуту за секунду(DC). \endrussian */
	normal int16u Decel			/**< \english Motor shaft deceleration, steps/s^2(stepper motor) or RPM/s(DC). Range: 1..65535. \endenglish \russian Торможение, заданное в шагах в секунду^2(ШД) или в оборотах в минуту за секунду(DC). Диапазон: 1..65535. \endrussian */
	calb float AntiplaySpeed	/**< \english Speed in antiplay mode. \endenglish \russian Скорость в режиме антилюфта. \endrussian */
	normal int32u AntiplaySpeed	/**< \english Speed in antiplay mode, full steps/s(stepper motor) or RPM(DC). Range: 0..100000. \endenglish \russian Скорость в режиме антилюфта, заданная в целых шагах/c(ШД) или в оборотах/с(DC). Диапазон: 0..100000. \endrussian */
	normal int8u uAntiplaySpeed	/**< \english Speed in antiplay mode, 1/256 microsteps/s. Used with stepper motor only. \endenglish \russian Скорость в режиме антилюфта, выраженная в 1/256 микрошагах в секунду. Используется только с шаговым мотором. \endrussian */
	reserved 10

/** $XIR
	* \english
	* Read engine settings.
	* This function fill structure with set of useful motor settings stored in controller's memory.
	* These settings specify motor shaft movement algorithm, list of limitations and rated characteristics.
	* @see set_engine_settings
	* @param id an identifier of device
	* @param[out] engine_settings engine settings
	* \endenglish
	* \russian
	* Чтение настроек мотора.
	* Настройки определяют номинальные значения напряжения, тока, скорости мотора, характер движения и тип мотора.
	* Пожалуйста, загружайте новые настройки когда вы меняете мотор, энкодер или позиционер.
	* Помните, что неправильные настройки мотора могут повредить оборудование.
	* @see set_engine_settings
	* @param id идентификатор устройства
	* @param[out] engine_settings структура с настройками мотора
	* \endrussian
	*/
/** $XIW
	* \english
	* Set engine settings.
	* This function send structure with set of engine settings to controller's memory.
	* These settings specify motor shaft movement algorithm, list of limitations and rated characteristics.
	* Use it when you change motor, encoder, positioner etc.
	* Please note that wrong engine settings lead to device malfunction, can lead to irreversible damage of board.
	* @see get_engine_settings
	* @param id an identifier of device
	* @param[in] engine_settings engine settings
	* \endenglish
	* \russian
	* Запись настроек мотора.
	* Настройки определяют номинальные значения напряжения, тока, скорости мотора, характер движения и тип мотора.
	* Пожалуйста, загружайте новые настройки когда вы меняете мотор, энкодер или позиционер.
	* Помните, что неправильные настройки мотора могут повредить оборудование.
	* @see get_engine_settings
	* @param id идентификатор устройства
	* @param[in] engine_settings структура с настройками мотора
	* \endrussian
	*/
/** $XIS
	* \english
	* Movement limitations and settings, related to the motor.
	* This structure contains useful motor settings.
	* These settings specify motor shaft movement algorithm, list of limitations and rated characteristics.
	* All boards are supplied with standard set of engine setting on controller's flash memory.
	* Please load new engine settings when you change motor, encoder, positioner etc.
	* Please note that wrong engine settings lead to device malfunction, can lead to irreversible damage of board.
	* \endenglish
	* \russian
	* Ограничения и настройки движения, связанные с двигателем.
	* Эта структура содержит настройки мотора.
	* Настройки определяют номинальные значения напряжения, тока, скорости мотора, характер движения и тип мотора.
	* Пожалуйста, загружайте новые настройки когда вы меняете мотор, энкодер или позиционер.
	* Помните, что неправильные настройки мотора могут повредить оборудование.
	* \endrussian
	* @see set_engine_settings
	* @see get_engine_settings
	*/
command "engine_settings" universal "eng" (34)
fields:
	int16u NomVoltage							/**< \english Rated voltage in tens of mV. Controller will keep the voltage drop on motor below this value if ENGINE_LIMIT_VOLT flag is set (used with DC only). \endenglish \russian Номинальное напряжение мотора в десятках мВ. Контроллер будет сохранять напряжение на моторе не выше номинального, если установлен флаг ENGINE_LIMIT_VOLT (используется только с DC двигателем). \endrussian */
	int16u NomCurrent							/**< \english Rated current. Controller will keep current consumed by motor below this value if ENGINE_LIMIT_CURR flag is set. Range: 15..8000 \endenglish \russian Номинальный ток через мотор. Ток стабилизируется для шаговых и может быть ограничен для DC(если установлен флаг ENGINE_LIMIT_CURR). Диапазон: 15..8000 \endrussian */
	calb float NomSpeed							/**< \english Nominal speed. Controller will keep motor speed below this value if ENGINE_LIMIT_RPM flag is set. \endenglish \russian Номинальная скорость. Контроллер будет сохранять скорость мотора не выше номинальной, если установлен флаг ENGINE_LIMIT_RPM. \endrussian */
	normal int32u NomSpeed						/**< \english Nominal (maximum) speed (in whole steps/s or rpm for DC and stepper motor as a master encoder). Controller will keep motor shaft RPM below this value if ENGINE_LIMIT_RPM flag is set. Range: 1..100000. \endenglish \russian Номинальная (максимальная) скорость (в целых шагах/с или rpm для DC и шагового двигателя в режиме ведущего энкодера). Контроллер будет сохранять скорость мотора не выше номинальной, если установлен флаг ENGINE_LIMIT_RPM. Диапазон: 1..100000. \endrussian */
	normal int8u uNomSpeed						/**< \english The fractional part of a nominal speed in microsteps (is only used with stepper motor). \endenglish \russian Микрошаговая часть номинальной скорости мотора (используется только с шаговым двигателем). \endrussian */
	int16u flag EngineFlags of EngineFlags		/**< \english Set of flags specify motor shaft movement algorithm and list of limitations \endenglish \russian Флаги, управляющие работой мотора. \endrussian */
	calb float Antiplay							/**< \english Number of pulses or steps for backlash (play) compensation procedure. Used if ENGINE_ANTIPLAY flag is set. \endenglish \russian Количество шагов двигателя или импульсов энкодера, на которое позиционер будет отъезжать от заданной позиции для подхода к ней с одной и той же стороны. Используется, если установлен флаг ENGINE_ANTIPLAY. \endrussian */
	normal int16s Antiplay						/**< \english Number of pulses or steps for backlash (play) compensation procedure. Used if ENGINE_ANTIPLAY flag is set. \endenglish \russian Количество шагов двигателя или импульсов энкодера, на которое позиционер будет отъезжать от заданной позиции для подхода к ней с одной и той же стороны. Используется, если установлен флаг ENGINE_ANTIPLAY. \endrussian */
	int8u flag MicrostepMode of MicrostepMode	/**< \english Settings of microstep mode(Used with stepper motor only). \endenglish \russian Настройки микрошагового режима(используется только с шаговым двигателем). \endrussian */
	int16u StepsPerRev							/**< \english Number of full steps per revolution(Used with stepper motor only). Range: 1..65535. \endenglish \russian Количество полных шагов на оборот(используется только с шаговым двигателем). Диапазон: 1..65535. \endrussian */
	reserved 12

/** $XIR
	* \english
	* Return engine type and driver type.
	* @param id an identifier of device
	* @param[out] EngineType engine type
	* @param[out] DriverType driver type
	* \endenglish
	* \russian
	* Возвращает информацию о типе мотора и силового драйвера.
	* @param id идентификатор устройства
	* @param[out] EngineType тип мотора
	* @param[out] DriverType тип силового драйвера
	* \endrussian
	*/
/** $XIW
	* \english
	* Set engine type and driver type.
	* @param id an identifier of device
	* @param[in] EngineType engine type
	* @param[in] DriverType driver type
	* \endenglish
	* \russian
	* Запись информации о типе мотора и типе силового драйвера.
	* @param id идентификатор устройства
	* @param[in] EngineType тип мотора
	* @param[in] DriverType тип силового драйвера
	* \endrussian
	*/
/** $XIS
	* \english
	* Engine type and driver type settings.
	* @param id an identifier of device
	* @param EngineType engine type
	* @param DriverType driver type
	* \endenglish
	* \russian
	* Настройки типа мотора и типа силового драйвера.
	* Эта структура содержит настройки типа мотора и типа силового драйвера.
	* @param id идентификатор устройства
	* @param EngineType тип мотора
	* @param DriverType тип силового драйвера
	* \endrussian
	*/
command "entype_settings" universal "ent" (14)
fields:
	int8u flag EngineType of EngineType	/**< \english Engine type \endenglish \russian Тип мотора \endrussian */
	int8u flag DriverType of DriverType	/**< \english Driver type \endenglish \russian Тип силового драйвера \endrussian */
	reserved 6

/** $XIR
	* \english
	* Read settings of step motor power control.
	* Used with stepper motor only.
	* @param id an identifier of device
	* @param[out] power_settings structure contains settings of step motor power control
	* \endenglish
	* \russian
	* Команда чтения параметров питания мотора. Используется только с шаговым двигателем.
	* Используется только с шаговым двигателем.
	* @param id идентификатор устройства
	* @param[out] power_settings структура, содержащая настройки питания шагового мотора
	* \endrussian
	*/
/** $XIW
	* \english
	* Set settings of step motor power control.
	* Used with stepper motor only.
	* @param id an identifier of device
	* @param[in] power_settings structure contains settings of step motor power control
	* \endenglish
	* \russian
	* Команда записи параметров питания мотора. Используется только с шаговым двигателем.
	* @param id идентификатор устройства
	* @param[in] power_settings структура, содержащая настройки питания шагового мотора
	* \endrussian
	*/
/** $XIS
	* \english
	* Step motor power settings.
	* \endenglish
	* \russian
	* Настройки питания шагового мотора.
	* \endrussian
	* @see set_move_settings
	* @see get_move_settings
	*/
command "power_settings" universal "pwr" (20)
fields:
	int8u HoldCurrent						/**< \english Current in holding regime, percent of nominal. Range: 0..100. \endenglish \russian Ток мотора в режиме удержания, в процентах от номинального. Диапазон: 0..100. \endrussian */
	int16u CurrReductDelay					/**< \english Time in ms from going to STOP state to reducting current. \endenglish \russian Время в мс от перехода в состояние STOP до уменьшения тока. \endrussian */
	int16u PowerOffDelay					/**< \english Time in s from going to STOP state to turning power off. \endenglish \russian Время в с от перехода в состояние STOP до отключения питания мотора. \endrussian */
	int16u CurrentSetTime					/**< \english Time in ms to reach nominal current. \endenglish \russian Время в мс, требуемое для набора номинального тока от 0% до 100%. \endrussian */
	int8u flag PowerFlags of PowerFlags		/**< \english Flags with parameters of power control. \endenglish \russian Флаги параметров управления питанием. \endrussian */
	reserved 6

/** $XIR
	* \english
	* Read protection settings.
	* @param id an identifier of device
	* @param[out] secure_settings critical parameter settings to protect the hardware
	* \endenglish
	* \russian
	* Команда записи установок защит.
	* @param id идентификатор устройства
	* @param[out] secure_settings настройки, определяющие максимально допустимые параметры, для защиты оборудования
	* \endrussian
	* @see status_t::flags
	*/
/** $XIW
	* \english
	* Set protection settings.
	* @param id an identifier of device
	* @param secure_settings structure with secure data
	* \endenglish
	* \russian
	* Команда записи установок защит.
	* @param id идентификатор устройства
	* @param secure_settings структура с настройками критических значений
	* \endrussian
	* @see status_t::flags
	*/
/** $XIS
	* \english
	* This structure contains raw analog data from ADC embedded on board.
	* These data used for device testing and deep recalibraton by manufacturer only.
	* \endenglish
	* \russian
	* Эта структура содержит необработанные данные с АЦП и нормированные значения.
	* Эти данные используются в сервисных целях для тестирования и калибровки устройства.
	* \endrussian
	* @see get_secure_settings
	* @see set_secure_settings
	*/
command "secure_settings" universal "sec" (28)
fields:
	int16u LowUpwrOff					/**< \english Lower voltage limit to turn off the motor, tens of mV. \endenglish \russian Нижний порог напряжения на силовой части для выключения, десятки мВ. \endrussian */
	int16u CriticalIpwr					/**< \english Maximum motor current which triggers ALARM state, in mA. \endenglish \russian Максимальный ток силовой части, вызывающий состояние ALARM, в мА. \endrussian */
	int16u CriticalUpwr					/**< \english Maximum motor voltage which triggers ALARM state, tens of mV. \endenglish \russian Максимальное напряжение на силовой части, вызывающее состояние ALARM, десятки мВ. \endrussian */
	int16u CriticalT					/**< \english Maximum temperature, which triggers ALARM state, in tenths of degrees Celcius. \endenglish \russian Максимальная температура контроллера, вызывающая состояние ALARM, в десятых долях градуса Цельсия.\endrussian */
	int16u CriticalIusb					/**< \english Maximum USB current which triggers ALARM state, in mA. \endenglish \russian Максимальный ток USB, вызывающий состояние ALARM, в мА. \endrussian */
	int16u CriticalUusb					/**< \english Maximum USB voltage which triggers ALARM state, tens of mV. \endenglish \russian Максимальное напряжение на USB, вызывающее состояние ALARM, десятки мВ. \endrussian */
	int16u MinimumUusb					/**< \english Minimum USB voltage which triggers ALARM state, tens of mV. \endenglish \russian Минимальное напряжение на USB, вызывающее состояние ALARM, десятки мВ. \endrussian */
	int8u flag Flags of SecureFlags		/**< \english Critical parameter flags. \endenglish \russian Флаги критических параметров. \endrussian */
	reserved 7

/**  $XIR
	* \english
	* Read border and limit switches settings.
	* @see set_edges_settings
	* @param id an identifier of device
	* @param[out] edges_settings edges settings, specify types of borders, motor behaviour and electrical behaviour of limit switches
	* \endenglish
	* \russian
	* Чтение настроек границ и концевых выключателей.
	* @see set_edges_settings
	* @param id идентификатор устройства
	* @param[out] edges_settings настройки, определяющие тип границ, поведение мотора при их достижении и параметры концевых выключателей
	* \endrussian
	*/
/** $XIW
	* \english
	* Set border and limit switches settings.
	* @see set_edges_settings
	* @param id an identifier of device
	* @param[in] edges_settings edges settings, specify types of borders, motor behaviour and electrical behaviour of limit switches
	* \endenglish
	* \russian
	* Запись настроек границ и концевых выключателей.
	* @see get_edges_settings
	* @param id идентификатор устройства
	* @param[in] edges_settings настройки, определяющие тип границ, поведение мотора при их достижении и параметры концевых выключателей
	* \endrussian
	*/
/**  $XIS
	* \english
	* Edges settings.
	* This structure contains border and limit switches settings.
	* Please load new engine settings when you change positioner etc.
	* Please note that wrong engine settings lead to device malfunction, can lead to irreversible damage of board.
	* \endenglish
	* \russian
	* Настройки границ.
	* Эта структура содержит настройки границ и концевых выключателей.
	* Пожалуйста, загружайте новые настройки когда вы меняете позиционер.
	* Помните, что неправильные настройки мотора могут повредить оборудование.
	* \endrussian
	* @see set_edges_settings
	* @see get_edges_settings
	*/
command "edges_settings" universal "eds" (26)
fields:
	int8u flag BorderFlags	of BorderFlags	/**< \english Border flags, specify types of borders and motor behaviour on borders. \endenglish \russian Флаги, определяющие тип границ и поведение мотора при их достижении. \endrussian */
	int8u flag EnderFlags of EnderFlags		/**< \english Ender flags, specify electrical behaviour of limit switches like order and pulled positions. \endenglish \russian Флаги, определяющие настройки концевых выключателей. \endrussian */
	calb float LeftBorder					/**< \english Left border position, used if BORDER_IS_ENCODER flag is set. \endenglish \russian Позиция левой границы, используется если установлен флаг BORDER_IS_ENCODER. \endrussian */
	normal int32s LeftBorder				/**< \english Left border position, used if BORDER_IS_ENCODER flag is set. \endenglish \russian Позиция левой границы, используется если установлен флаг BORDER_IS_ENCODER. \endrussian */
	normal int16s uLeftBorder				/**< \english Left border position in 1/256 microsteps(used with stepper motor only). Range: -255..255. \endenglish \russian Позиция левой границы в 1/256 микрошагах( используется только с шаговым двигателем). Диапазон: -255..255. \endrussian */
	calb float RightBorder					/**< \english Right border position, used if BORDER_IS_ENCODER flag is set. \endenglish \russian Позиция правой границы, используется если установлен флаг BORDER_IS_ENCODER. \endrussian */
	normal int32s RightBorder				/**< \english Right border position, used if BORDER_IS_ENCODER flag is set. \endenglish \russian Позиция правой границы, используется если установлен флаг BORDER_IS_ENCODER. \endrussian */
	normal int16s uRightBorder				/**< \english Right border position in 1/256 microsteps. Used with stepper motor only. Range: -255..255. \endenglish \russian Позиция правой границы в 1/256 микрошагах (используется только с шаговым двигателем). Диапазон: -255..255. \endrussian */
	reserved 6

/**  $XIR
	* \english
	* Read PID settings.
	* This function fill structure with set of motor PID settings stored in controller's memory.
	* These settings specify behaviour of PID routine for positioner.
	* These factors are slightly different for different positioners.
	* All boards are supplied with standard set of PID setting on controller's flash memory.
	* @see set_pid_settings
	* @param id an identifier of device
	* @param[out] pid_settings pid settings
	* \endenglish
	* \russian
	* Чтение ПИД коэффициентов.
	* Эти коэффициенты определяют поведение позиционера.
	* Коэффициенты различны для разных позиционеров.
	* @see set_pid_settings
	* @param id идентификатор устройства
	* @param[out] pid_settings настройки ПИД
	* \endrussian
	*/
/**  $XIW
	* \english
	* Set PID settings.
	* This function send structure with set of PID factors to controller's memory.
	* These settings specify behaviour of PID routine for positioner.
	* These factors are slightly different for different positioners.
	* All boards are supplied with standard set of PID setting on controller's flash memory.
	* Please use it for loading new PID settings when you change positioner.
	* Please note that wrong PID settings lead to device malfunction.
	* @see get_pid_settings
	* @param id an identifier of device
	* @param[in] pid_settings pid settings
	* \endenglish
	* \russian
	* Запись ПИД коэффициентов.
	* Эти коэффициенты определяют поведение позиционера.
	* Коэффициенты различны для разных позиционеров.
	* Пожалуйста, загружайте новые настройки, когда вы меняете мотор или позиционер.
	* @see get_pid_settings
	* @param id идентификатор устройства
	* @param[in] pid_settings настройки ПИД
	* \endrussian
	*/
/**  $XIS
	* \english
	* PID settings.
	* This structure contains factors for PID routine.
	* It specify behaviour of PID routine for voltage.
	* These factors are slightly different for different positioners.
	* All boards are supplied with standard set of PID setting on controller's flash memory.
	* Please load new PID settings when you change positioner.
	* Please note that wrong PID settings lead to device malfunction.
	* \endenglish
	* \russian
	* Настройки ПИД.
	* Эта структура содержит коэффициенты для ПИД регулятора.
	* Они определяют работу ПИД контура напряжения.
	* Эти коэффициенты хранятся во flash памяти памяти контроллера.
	* Пожалуйста, загружайте новые настройки, когда вы меняете мотор или позиционер.
	* Помните, что неправильные настройки ПИД контуров могут повредить оборудование.
	* \endrussian

	* @see set_pid_settings
	* @see get_pid_settings
	*/
command "pid_settings" universal "pid" (48)
fields:
	int16u KpU		/**< \english Proportional gain for voltage PID routine \endenglish \russian Пропорциональный коэффициент ПИД контура по напряжению \endrussian */
	int16u KiU		/**< \english Integral gain for voltage PID routine \endenglish \russian Интегральный коэффициент ПИД контура по напряжению \endrussian */
	int16u KdU		/**< \english Differential gain for voltage PID routine \endenglish \russian Дифференциальный коэффициент ПИД контура по напряжению \endrussian */
	float Kpf		/**< \english Proportional gain for BLDC position PID routine \endenglish \russian Пропорциональный коэффициент ПИД контура по позиции для BLDC \endrussian */
	float Kif		/**< \english Integral gain for BLDC position PID routine \endenglish \russian Интегральный коэффициент ПИД контура по позиции для BLDC \endrussian */
	float Kdf		/**< \english Differential gain for BLDC position PID routine \endenglish \russian Дифференциальный коэффициент ПИД контура по позиции для BLDC \endrussian */
	reserved 24

/**  $XIR
	* \english
	* Read input synchronization settings.
	* This function fill structure with set of input synchronization settings, modes, periods and flags, that specify behaviour of input synchronization.
	* All boards are supplied with standard set of these settings.
	* @see set_sync_in_settings
	* @param id an identifier of device
	* @param[out] sync_in_settings synchronization settings
	* \endenglish
	* \russian
	* Чтение настроек для входного импульса синхронизации.
	* Эта функция считывает структуру с настройками синхронизации, определяющими поведение входа синхронизации, в память контроллера.
	* @see set_sync_in_settings
	* @param id идентификатор устройства
	* @param[out] sync_in_settings настройки синхронизации
	* \endrussian
	*/
/**  $XIW
	* \english
	* Set input synchronization settings.
	* This function send structure with set of input synchronization settings, that specify behaviour of input synchronization, to controller's memory.
	* All boards are supplied with standard set of these settings.
	* @see get_sync_in_settings
	* @param id an identifier of device
	* @param[in] sync_in_settings synchronization settings
	* \endenglish
	* \russian
	* Запись настроек для входного импульса синхронизации.
	* Эта функция записывает структуру с настройками входного импульса синхронизации, определяющими поведение входа синхронизации, в память контроллера.
	* @see get_sync_in_settings
	* @param id идентификатор устройства
	* @param[in] sync_in_settings настройки синхронизации
	* \endrussian
	*/
/** $XIS
	* \english
	* Synchronization settings.
	* This structure contains all synchronization settings, modes, periods and flags.
	* It specifes behaviour of input synchronization.
	* All boards are supplied with standard set of these settings.
	* \endenglish
	* \russian
	* Настройки входной синхронизации.
	* Эта структура содержит все настройки, определяющие поведение входа синхронизации.
	* \endrussian
	* @see get_sync_in_settings
	* @see set_sync_in_settings
	*/

command "sync_in_settings" universal "sni" (28)
fields:
	int8u flag SyncInFlags of SyncInFlags		/**< \english Input synchronization flags \endenglish \russian Флаги синхронизации входа \endrussian */
	int16u ClutterTime							/**< \english Input synchronization pulse dead time (mks). \endenglish \russian Минимальная длительность входного импульса синхронизации для защиты от дребезга (мкс). \endrussian */
	calb float Position							/**< \english Desired position or shift. \endenglish \russian Желаемая позиция или смещение. \endrussian */
	normal int32s Position						/**< \english Desired position or shift (whole steps) \endenglish \russian Желаемая позиция или смещение (целая часть) \endrussian */
	normal int16s uPosition						/**< \english The fractional part of a position or shift in microsteps. Is used with stepper motor. Range: -255..255. \endenglish \russian Дробная часть позиции или смещения в микрошагах. Используется только с шаговым двигателем. Диапазон: -255..255. \endrussian */
	calb float Speed							/**< \english Target speed. \endenglish \russian Заданная скорость. \endrussian */
	normal int32u Speed							/**< \english Target speed (for stepper motor: steps/s, for DC: rpm). Range: 0..100000. \endenglish \russian Заданная скорость (для ШД: шагов/c, для DC: rpm). Диапазон: 0..100000. \endrussian */
	normal int8u uSpeed							/**< \english Target speed in microsteps/s. Using with stepper motor only. \endenglish \russian Заданная скорость в микрошагах в секунду. Используется только с шаговым мотором. \endrussian */
	reserved 8

/** $XIR
	* \english
	* Read output synchronization settings.
	* This function fill structure with set of output synchronization settings, modes, periods and flags, that specify behaviour of output synchronization.
	* All boards are supplied with standard set of these settings.
	* @see set_sync_out_settings
	* @param id an identifier of device
	* @param[out] sync_out_settings synchronization settings
	* \endenglish
	* \russian
	* Чтение настроек для выходного импульса синхронизации.
	* Эта функция считывает структуру с настройками синхронизации, определяющими поведение выхода синхронизации, в память контроллера.
	* \endrussian
	*/
/** $XIW
	* \english
	* Set output synchronization settings.
	* This function send structure with set of output synchronization settings, that specify behaviour of output synchronization, to controller's memory.
	* All boards are supplied with standard set of these settings.
	* @see get_sync_out_settings
	* @param id an identifier of device
	* @param[in] sync_out_settings synchronization settings
	* \endenglish
	* \russian
	* Запись настроек для выходного импульса синхронизации.
	* Эта функция записывает структуру с настройками выходного импульса синхронизации, определяющими поведение вывода синхронизации, в память контроллера.
	* @see get_sync_in_settings
	* @param id идентификатор устройства
	* @param[in] sync_in_settings настройки синхронизации
	* \endrussian
	*/
/** $XIS
	* \english
	* Synchronization settings.
	* This structure contains all synchronization settings, modes, periods and flags.
	* It specifes behaviour of output synchronization.
	* All boards are supplied with standard set of these settings.
	* \endenglish
	* \russian
	* Настройки выходной синхронизации.
	* Эта структура содержит все настройки, определяющие поведение выхода синхронизации.
	* \endrussian
	* @see get_sync_out_settings
	* @see set_sync_out_settings
	*/

command "sync_out_settings" universal "sno" (16)
fields:
	int8u flag SyncOutFlags of SyncOutFlags	/**< \english Output synchronization flags \endenglish \russian Флаги синхронизации выхода \endrussian */
	int16u SyncOutPulseSteps				/**< \english This value specifies duration of output pulse. It is measured microseconds when SYNCOUT_IN_STEPS flag is cleared or in encoder pulses or motor steps when SYNCOUT_IN_STEPS is set. \endenglish \russian Определяет длительность выходных импульсов в шагах/импульсах энкодера, когда установлен флаг SYNCOUT_IN_STEPS, или в микросекундах если флаг сброшен. \endrussian */
	int16u SyncOutPeriod					/**< \english This value specifies number of encoder pulses or steps between two output synchronization pulses when SYNCOUT_ONPERIOD is set. \endenglish \russian Период генерации импульсов, используется при установленном флаге SYNCOUT_ONPERIOD. \endrussian */
	calb float Accuracy						/**< \english This is the neighborhood around the target coordinates, which is getting hit in the target position and the momentum generated by the stop. \endenglish \russian Это окрестность вокруг целевой координаты, попадание в которую считается попаданием в целевую позицию и генерируется импульс по остановке. \endrussian */
	normal int32u Accuracy					/**< \english This is the neighborhood around the target coordinates, which is getting hit in the target position and the momentum generated by the stop. \endenglish \russian Это окрестность вокруг целевой координаты, попадание в которую считается попаданием в целевую позицию и генерируется импульс по остановке. \endrussian */
	normal int8u uAccuracy					/**< \english This is the neighborhood around the target coordinates in micro steps (only used with stepper motor). \endenglish \russian Это окрестность вокруг целевой координаты в микрошагах (используется только с шаговым двигателем). \endrussian */

/** $XIR
	* \english
	* Read EXTIO settings.
	* This function reads a structure with a set of EXTIO settings from controller's memory.
	* @see set_extio_settings
	* @param id an identifier of device
	* @param[out] extio_settings EXTIO settings
	* \endenglish
	* \russian
	* Команда чтения параметров настройки режимов внешнего ввода/вывода.
	* @see set_extio_settings
	* @param id идентификатор устройства
	* @param[out] extio_settings настройки EXTIO
	* \endrussian
	*/
/** $XIW
	* \english
	* Set EXTIO settings.
	* This function writes a structure with a set of EXTIO settings to controller's memory.
	* By default input event are signalled through rising front and output states are signalled by high logic state.
	* @see get_extio_settings
	* @param id an identifier of device
	* @param[in] extio_settings EXTIO settings
	* \endenglish
	* \russian
	* Команда записи параметров настройки режимов внешнего ввода/вывода.
	* Входные события обрабатываются по фронту. Выходные состояния сигнализируются логическим состоянием.
	* По умолчанию нарастающий фронт считается моментом подачи входного сигнала, а единичное состояние считается активным выходом.
	* @see get_extio_settings
	* @param id идентификатор устройства
	* @param[in] extio_settings настройки EXTIO
	* \endrussian
	*/
/** $XIS
	* \english
	* EXTIO settings.
	* This structure contains all EXTIO settings.
	* By default input event are signalled through rising front and output states are signalled by high logic state.
	* \endenglish
	* \russian
	* Настройки EXTIO.
	* Эта структура содержит все настройки, определяющие поведение ножки EXTIO.
	* Входные события обрабатываются по фронту. Выходные состояния сигнализируются логическим состоянием.
	* По умолчанию нарастающий фронт считается моментом подачи входного сигнала, а единичное состояние считается активным выходом.
	* \endrussian
	* @see get_extio_settings
	* @see set_extio_settings
	*/

command "extio_settings" universal "eio" (18)
fields:
	int8u flag EXTIOSetupFlags of ExtioSetupFlags	/**< \english Configuration flags of the external I-O \endenglish \russian Флаги настройки работы внешнего ввода-вывода \endrussian */
	int8u flag EXTIOModeFlags of ExtioModeFlags		/**< \english Flags mode settings external I-O \endenglish \russian Флаги настройки режимов внешнего ввода-вывода \endrussian */
	reserved 10

/** $XIR
	* \english
	* Read settings of brake control.
	* @param id an identifier of device
	* @param[out] brake_settings structure contains settings of brake control
	* \endenglish
	* \russian
	* Чтение настроек управления тормозом.
	* @param id идентификатор устройства
	* @param[out] brake_settings структура, содержащая настройки управления тормозом
	* \endrussian
	*/
/** $XIW
	* \english
	* Set settings of brake control.
	* @param id an identifier of device
	* @param[in] brake_settings structure contains settings of brake control
	* \endenglish
	* \russian
	* Запись настроек управления тормозом.
	* @param id идентификатор устройства
	* @param[in] brake_settings структура, содержащая настройки управления тормозом
	* \endrussian
	*/
/** $XIS
	* \english
	* Brake settings.
	* This structure contains parameters of brake control.
	* \endenglish
	* \russian
	* Настройки тормоза.
	* Эта структура содержит параметры управления тормозом.
	* \endrussian
	* @see set_brake_settings
	* @see get_brake_settings
	*/
command "brake_settings" universal "brk" (25)
fields:
	int16u t1							/**< \english Time in ms between turn on motor power and turn off brake. \endenglish \russian Время в мс между включением питания мотора и отключением тормоза. \endrussian */
	int16u t2							/**< \english Time in ms between turn off brake and moving readiness. All moving commands will execute after this interval. \endenglish \russian Время в мс между отключением тормоза и готовностью к движению. Все команды движения начинают выполняться только по истечении этого времени. \endrussian */
	int16u t3							/**< \english Time in ms between motor stop and turn on brake. \endenglish \russian Время в мс между остановкой мотора и включением тормоза. \endrussian */
	int16u t4							/**< \english Time in ms between turn on brake and turn off motor power. \endenglish \russian Время в мс между включением тормоза и отключением питания мотора. \endrussian */
	int8u flag BrakeFlags of BrakeFlags	/**< \english Flags. \endenglish \russian Флаги. \endrussian */
	reserved 10

/** $XIR
	* \english
	* Read settings of motor control.
	* When choosing CTL_MODE = 1 switches motor control with the joystick.
	* In this mode, the joystick to the maximum engine tends
	* Move at MaxSpeed [i], where i = 0 if the previous use
	* This mode is not selected another i. Buttons switch the room rate i.
	* When CTL_MODE = 2 is switched on motor control using the
	* Left / right. When you click on the button motor starts to move in the appropriate direction at a speed MaxSpeed [0],
	* at the end of time Timeout [i] motor move at a speed MaxSpeed [i+1]. at
	* Transition from MaxSpeed [i] on MaxSpeed [i +1] to acceleration, as usual.
	* @param id an identifier of device
	* @param[out] control_settings structure contains settings motor control by joystick or buttons left/right.
	* \endenglish
	* \russian
	* Чтение настроек управления мотором.
	* При выборе CTL_MODE=1 включается управление мотором с помощью джойстика.
	* В этом режиме при отклонении джойстика на максимум двигатель стремится
	* двигаться со скоростью MaxSpeed [i], где i=0, если предыдущим использованием
	* этого режима не было выбрано другое i. Кнопки переключают номер скорости i.
	* При выборе CTL_MODE=2 включается управление мотором с помощью кнопок
	* left/right. При нажатии на кнопки двигатель начинает двигаться в соответствующую сторону со скоростью MaxSpeed [0], по истечении времени Timeout[i] мотор
	* двигается со скоростью MaxSpeed [i+1]. При
	* переходе от MaxSpeed [i] на MaxSpeed [i+1] действует ускорение, как обычно.
	* @param id идентификатор устройства
	* @param[out] control_settings структура, содержащая настройки управления мотором с помощью джойстика или кнопок влево/вправо.
	* \endrussian
	*/
/** $XIW
	* \english
	* Set settings of motor control.
	* When choosing CTL_MODE = 1 switches motor control with the joystick.
	* In this mode, the joystick to the maximum engine tends
	* Move at MaxSpeed [i], where i = 0 if the previous use
	* This mode is not selected another i. Buttons switch the room rate i.
	* When CTL_MODE = 2 is switched on motor control using the
	* Left / right. When you click on the button motor starts to move in the appropriate direction at a speed MaxSpeed [0],
	* at the end of time Timeout [i] motor move at a speed MaxSpeed [i+1]. at
	* Transition from MaxSpeed [i] on MaxSpeed [i +1] to acceleration, as usual.
	* @param id an identifier of device
	* @param[in] control_settings structure contains settings motor control by joystick or buttons left/right.
	* \endenglish
	* \russian
	* Запись настроек управления мотором.
	* При выборе CTL_MODE=1 включается управление мотором с помощью джойстика.
	* В этом режиме при отклонении джойстика на максимум двигатель стремится
	* двигаться со скоростью MaxSpeed [i], где i=0, если предыдущим использованием
	* этого режима не было выбрано другое i. Кнопки переключают номер скорости i.
	* При выборе CTL_MODE=2 включается управление мотором с помощью кнопок
	* left/right. При нажатии на кнопки двигатель начинает двигаться в соответствующую сторону со скоростью MaxSpeed [0], по истечении времени Timeout[i] мотор
	* двигается со скоростью MaxSpeed [i+1]. При
	* переходе от MaxSpeed [i] на MaxSpeed [i+1] действует ускорение, как обычно.
	* @param id идентификатор устройства
	* @param[in] control_settings структура, содержащая настройки управления мотором с помощью джойстика или кнопок влево/вправо.
	* \endrussian
	*/
/** $XIS
	* \english
	* Control settings.
	* This structure contains control parameters.
	* When choosing CTL_MODE=1 switches motor control with the joystick.
	* In this mode, the joystick to the maximum engine tends
	* Move at MaxSpeed [i], where i=0 if the previous use
	* This mode is not selected another i. Buttons switch the room rate i.
	* When CTL_MODE=2 is switched on motor control using the
	* Left / right. When you click on the button motor starts to move in the appropriate direction at a speed MaxSpeed [0],
	* at the end of time Timeout[i] motor move at a speed MaxSpeed [i+1]. at
	* Transition from MaxSpeed [i] on MaxSpeed [i+1] to acceleration, as usual.
	* The figure above shows the sensitivity of the joystick feature on its position.
	* \endenglish
	* \russian
	* Настройки управления.
	* При выборе CTL_MODE=1 включается управление мотором с помощью джойстика.
	* В этом режиме при отклонении джойстика на максимум двигатель стремится
	* двигаться со скоростью MaxSpeed [i], где i=0, если предыдущим использованием
	* этого режима не было выбрано другое i. Кнопки переключают номер скорости i.
	* При выборе CTL_MODE=2 включается управление мотором с помощью кнопок
	* left/right. При нажатии на кнопки двигатель начинает двигаться в соответствующую сторону со скоростью MaxSpeed [0], по истечении времени Timeout[i] мотор
	* двигается со скоростью MaxSpeed [i+1]. При
	* переходе от MaxSpeed [i] на MaxSpeed [i+1] действует ускорение, как обычно.
	* \endrussian
	* @see set_control_settings
	* @see get_control_settings
	*/
command "control_settings" universal "ctl"(93)
fields:
	calb float MaxSpeed [10]	/**< \english Array of speeds using with joystick and button control. \endenglish \russian Массив скоростей, использующийся при управлении джойстиком или кнопками влево/вправо. \endrussian */
	normal int32u MaxSpeed [10]	/**< \english Array of speeds (full step) using with joystick and button control. Range: 0..100000. \endenglish \russian Массив скоростей (в полных шагах), использующийся при управлении джойстиком или кнопками влево/вправо. Диапазон: 0..100000. \endrussian */
	normal int8u uMaxSpeed [10]	/**< \english Array of speeds (1/256 microstep) using with joystick and button control. \endenglish \russian Массив скоростей (в 1/256 микрошагах), использующийся при управлении джойстиком или кнопками влево/вправо. \endrussian */
	int16u Timeout [9]			/**< \english timeout[i] is time in ms, after that max_speed[i+1] is applying. It is using with buttons control only. \endenglish \russian timeout[i] - время в мс, по истечении которого устанавливается скорость max_speed[i+1] (используется только при управлении кнопками). \endrussian */
	int16u MaxClickTime			/**< \english Maximum click time. Prior to the expiration of this time the first speed isn't enabled. \endenglish \russian Максимальное время клика. До истечения этого времени первая скорость не включается. \endrussian */
	int16u flag Flags of ControlFlags	/**< \english Flags. \endenglish \russian Флаги. \endrussian */
	calb float DeltaPosition			/**< \english Shift (delta) of position \endenglish \russian Смещение (дельта) позиции \endrussian */
	normal int32s DeltaPosition			/**< \english Shift (delta) of position \endenglish \russian Смещение (дельта) позиции \endrussian */
	normal int16s uDeltaPosition		/**< \english Fractional part of the shift in micro steps. Is only used with stepper motor. Range: -255..255. \endenglish \russian Дробная часть смещения в микрошагах. Используется только с шаговым двигателем. Диапазон: -255..255. \endrussian */
	reserved 9

/** $XIR
	* \english
	* Read settings of joystick.
	* If joystick position is outside DeadZone limits from the central position a movement with speed,
	* defined by the joystick DeadZone edge to 100% deviation, begins. Joystick positions inside DeadZone limits
	* correspond to zero speed (soft stop of motion) and positions beyond Low and High limits correspond MaxSpeed [i]
	* or -MaxSpeed [i] (see command SCTL), where i = 0 by default and can be changed with left/right buttons (see command SCTL).
	* If next speed in list is zero (both integer and microstep parts), the button press is ignored. First speed in list shouldn't be zero.
	* The DeadZone ranges are illustrated on the following picture.
	* !/attachments/download/5563/range25p.png!
	* The relationship between the deviation and the rate is exponential,
	* allowing no switching speed combine high mobility and accuracy. The following picture illustrates this:
	* !/attachments/download/3092/ExpJoystick.png!
	* The nonlinearity parameter is adjustable. Setting it to zero makes deviation/speed relation linear.
	* @param id an identifier of device
	* @param[out] joystick_settings structure contains joystick settings
	* \endenglish
	* \russian
	* Чтение настроек джойстика.
	* При отклонении джойстика более чем на DeadZone от центрального положения начинается движение со скоростью,
	* определяемой отклонением джойстика от DeadZone до 100% отклонения, причем отклонению DeadZone соответствует
	* нулевая скорость, а 100% отклонения соответствует MaxSpeed [i] (см. команду SCTL), где i=0, если предыдущим
	* использованием этого режима не было выбрано другое i.
	* Если следующая скорость в таблице скоростей нулевая (целая и микрошаговая части), то перехода на неё не происходит.
	* DeadZone вычисляется в десятых долях процента отклонения
	* от центра (JoyCenter) до правого или левого максимума. Расчёт DeadZone проиллюстрирован на графике: !/attachments/download/5563/range25p.png!
	* Зависимость между отклонением и скоростью экспоненциальная,
	* что позволяет без переключения режимов скорости сочетать высокую подвижность и точность. На графике ниже показан
	* пример экспоненциальной зависимости скорости и работы мертвой зоны.
	* !/attachments/download/3092/ExpJoystick.png!
	* Параметр нелинейнойсти можно менять. Нулевой параметр нелинейности соответствует линейной зависимости.
	* @param id идентификатор устройства
	* @param[out] joystick_settings структура, содержащая настройки джойстика
	* \endrussian
	*/
/** $XIW
	* \english
	* Set settings of joystick.
	* If joystick position is outside DeadZone limits from the central position a movement with speed,
	* defined by the joystick DeadZone edge to 100% deviation, begins. Joystick positions inside DeadZone limits
	* correspond to zero speed (soft stop of motion) and positions beyond Low and High limits correspond MaxSpeed [i]
	* or -MaxSpeed [i] (see command SCTL), where i = 0 by default and can be changed with left/right buttons (see command SCTL).
	* If next speed in list is zero (both integer and microstep parts), the button press is ignored. First speed in list shouldn't be zero.
	* The DeadZone ranges are illustrated on the following picture.
	* !/attachments/download/5563/range25p.png!
	* The relationship between the deviation and the rate is exponential,
	* allowing no switching speed combine high mobility and accuracy. The following picture illustrates this:
	* !/attachments/download/3092/ExpJoystick.png!
	* The nonlinearity parameter is adjustable. Setting it to zero makes deviation/speed relation linear.
	* @param id an identifier of device
	* @param[in] joystick_settings structure contains joystick settings
	* \endenglish
	* \russian
	* Запись настроек джойстика.
	* При отклонении джойстика более чем на DeadZone от центрального положения начинается движение со скоростью,
	* определяемой отклонением джойстика от DeadZone до 100% отклонения, причем отклонению DeadZone соответствует
	* нулевая скорость, а 100% отклонения соответствует MaxSpeed [i] (см. команду SCTL), где i=0, если предыдущим
	* использованием этого режима не было выбрано другое i.
	* Если следующая скорость в таблице скоростей нулевая (целая и микрошаговая части), то перехода на неё не происходит.
	* DeadZone вычисляется в десятых долях процента отклонения
	* от центра (JoyCenter) до правого или левого максимума. Расчёт DeadZone проиллюстрирован на графике: !/attachments/download/5563/range25p.png!
	* Зависимость между отклонением и скоростью экспоненциальная,
	* что позволяет без переключения режимов скорости сочетать высокую подвижность и точность. На графике ниже показан
	* пример экспоненциальной зависимости скорости и работы мертвой зоны.
	* !/attachments/download/3092/ExpJoystick.png!
	* Параметр нелинейнойсти можно менять. Нулевой параметр нелинейности соответствует линейной зависимости.
	* @param id идентификатор устройства
	* @param[in] joystick_settings структура, содержащая настройки джойстика
	* \endrussian
	*/
/** $XIS
	* \english
	* Joystick settings.
	* This structure contains joystick parameters.
	* If joystick position is outside DeadZone limits from the central position a movement with speed,
	* defined by the joystick DeadZone edge to 100% deviation, begins. Joystick positions inside DeadZone limits
	* correspond to zero speed (soft stop of motion) and positions beyond Low and High limits correspond MaxSpeed [i]
	* or -MaxSpeed [i] (see command SCTL), where i = 0 by default and can be changed with left/right buttons (see command SCTL).
	* If next speed in list is zero (both integer and microstep parts), the button press is ignored. First speed in list shouldn't be zero.
	* The relationship between the deviation and the rate is exponential,
	* allowing no switching speed combine high mobility and accuracy.
	* \endenglish
	* \russian
	* Настройки джойстика.
	* Команда чтения настроек и калибровки джойстика.
	* При отклонении джойстика более чем на DeadZone от центрального положения начинается движение со скоростью,
	* определяемой отклонением джойстика от DeadZone до 100% отклонения, причем отклонению DeadZone соответствует
	* нулевая скорость, а 100% отклонения соответствует MaxSpeed [i] (см. команду SCTL), где i=0, если предыдущим
	* использованием этого режима не было выбрано другое i.
	* Если следующая скорость в таблице скоростей нулевая (целая и микрошаговая части), то перехода на неё не происходит.
	* DeadZone вычисляется в десятых долях процента отклонения
	* от центра (JoyCenter) до правого или левого максимума. Зависимость между отклонением и скоростью экспоненциальная,
	* что позволяет без переключения режимов скорости сочетать высокую подвижность и точность.
	* \endrussian
	* @see set_joystick_settings
	* @see get_joystick_settings
	*/
command "joystick_settings" universal "joy"(22)
fields:
	int16u JoyLowEnd					/**< \english Joystick lower end position. Range: 0..10000. \endenglish \russian Значение в шагах джойстика, соответствующее нижней границе диапазона отклонения устройства. Должно лежать в пределах. Диапазон: 0..10000. \endrussian */
	int16u JoyCenter					/**< \english Joystick center position. Range: 0..10000. \endenglish \russian Значение в шагах джойстика, соответствующее неотклонённому устройству. Должно лежать в пределах. Диапазон: 0..10000. \endrussian */
	int16u JoyHighEnd					/**< \english Joystick higher end position. Range: 0..10000. \endenglish \russian Значение в шагах джойстика, соответствующее верхней границе диапазона отклонения устройства. Должно лежать в пределах. Диапазон: 0..10000. \endrussian */
	int8u ExpFactor						/**< \english Exponential nonlinearity factor. \endenglish \russian Фактор экспоненциальной нелинейности отклика джойстика. \endrussian */
	int8u DeadZone						/**< \english Joystick dead zone. \endenglish \russian Отклонение от среднего положения, которое не вызывает начала движения (в десятых долях процента). Максимальное мёртвое отклонение +-25.5%, что составляет половину рабочего диапазона джойстика. \endrussian */
	int8u flag JoyFlags of JoyFlags		/**< \english Joystick control flags. \endenglish \russian Флаги управления джойстиком. \endrussian */
	reserved 7

/** $XIR
	* \english
	* Read settings of control position(is only used with stepper motor).
	* When controlling the step motor with encoder (CTP_BASE 0) it is possible
	* to detect the loss of steps. The controller knows the number of steps per
	* revolution (GENG :: StepsPerRev) and the encoder resolution (GFBS :: IPT).
	* When the control (flag CTP_ENABLED), the controller stores the current position
	* in the footsteps of SM and the current position of the encoder. Further, at
	* each step of the position encoder is converted into steps and if the difference
	* is greater CTPMinError, a flag STATE_CTP_ERROR.
	* When controlling the step motor with speed sensor (CTP_BASE 1), the position is
	* controlled by him. The active edge of input clock controller stores the current
	* value of steps. Further, at each turn checks how many steps shifted. When a
	* mismatch CTPMinError a flag STATE_CTP_ERROR.
	* @param id an identifier of device
	* @param[out] ctp_settings structure contains settings of control position
	* \endenglish
	* \russian
	* Чтение настроек контроля позиции(для шагового двигателя).
	* При управлении ШД с энкодером
	* (CTP_BASE 0) появляется возможность обнаруживать потерю шагов. Контроллер
	* знает кол-во шагов на оборот (GENG::StepsPerRev) и разрешение энкодера
	* (GFBS::IPT). При включении контроля (флаг CTP_ENABLED), контроллер запоминает
	* текущую позицию в шагах ШД и текущую позицию энкодера. Далее, на каждом шаге
	* позиция энкодера преобразовывается в шаги и если разница оказывается больше
	* CTPMinError, устанавливается флаг STATE_CTP_ERROR.
	* При управлении ШД с датчиком оборотов (CTP_BASE 1), позиция контролируется по нему.
	* По активному фронту на входе синхронизации контроллер запоминает текущее значение
	* шагов. Далее, при каждом обороте проверяет, на сколько шагов сместились. При
	* рассогласовании более CTPMinError устанавливается флаг STATE_CTP_ERROR.
	* @param id идентификатор устройства
	* @param[out] ctp_settings структура, содержащая настройки контроля позиции
	* \endrussian
	*/
/** $XIW
	* \english
	* Set settings of control position(is only used with stepper motor).
	* When controlling the step motor with encoder (CTP_BASE 0) it is possible
	* to detect the loss of steps. The controller knows the number of steps per
	* revolution (GENG :: StepsPerRev) and the encoder resolution (GFBS :: IPT).
	* When the control (flag CTP_ENABLED), the controller stores the current position
	* in the footsteps of SM and the current position of the encoder. Further, at
	* each step of the position encoder is converted into steps and if the difference
	* is greater CTPMinError, a flag STATE_CTP_ERROR.
	* When controlling the step motor with speed sensor (CTP_BASE 1), the position is
	* controlled by him. The active edge of input clock controller stores the current
	* value of steps. Further, at each turn checks how many steps shifted. When a
	* mismatch CTPMinError a flag STATE_CTP_ERROR.
	* @param id an identifier of device
	* @param[in] ctp_settings structure contains settings of control position
	* \endenglish
	* \russian
	* Запись настроек контроля позиции(для шагового двигателя).
	* При управлении ШД с энкодером
	* (CTP_BASE 0) появляется возможность обнаруживать потерю шагов. Контроллер
	* знает кол-во шагов на оборот (GENG::StepsPerRev) и разрешение энкодера
	* (GFBS::IPT). При включении контроля (флаг CTP_ENABLED), контроллер запоминает
	* текущую позицию в шагах ШД и текущую позицию энкодера. Далее, на каждом шаге
	* позиция энкодера преобразовывается в шаги и если разница оказывается больше
	* CTPMinError, устанавливается флаг STATE_CTP_ERROR.
	* При управлении ШД с датчиком оборотов (CTP_BASE 1), позиция контролируется по нему.
	* По активному фронту на входе синхронизации контроллер запоминает текущее значение
	* шагов. Далее, при каждом обороте проверяет, на сколько шагов сместились. При
	* рассогласовании более CTPMinError устанавливается флаг STATE_CTP_ERROR.
	* @param id идентификатор устройства
	* @param[in] ctp_settings структура, содержащая настройки контроля позиции
	* \endrussian
	*/
/** $XIS
	* \english
	* Control position settings(is only used with stepper motor).
	* When controlling the step motor with encoder (CTP_BASE 0) it is possible
	* to detect the loss of steps. The controller knows the number of steps per
	* revolution (GENG :: StepsPerRev) and the encoder resolution (GFBS :: IPT).
	* When the control (flag CTP_ENABLED), the controller stores the current position
	* in the footsteps of SM and the current position of the encoder. Further, at
	* each step of the position encoder is converted into steps and if the difference
	* is greater CTPMinError, a flag STATE_CTP_ERROR and set ALARM state.
	* When controlling the step motor with speed sensor (CTP_BASE 1), the position is
	* controlled by him. The active edge of input clock controller stores the current
	* value of steps. Further, at each turn checks how many steps shifted. When a
	* mismatch CTPMinError a flag STATE_CTP_ERROR and set ALARM state.
	* \endenglish
	* \russian
	* Настройки контроля позиции(для шагового двигателя).
	* При управлении ШД с энкодером
	* (CTP_BASE 0) появляется возможность обнаруживать потерю шагов. Контроллер
	* знает кол-во шагов на оборот (GENG::StepsPerRev) и разрешение энкодера
	* (GFBS::IPT). При включении контроля (флаг CTP_ENABLED), контроллер запоминает
	* текущую позицию в шагах ШД и текущую позицию энкодера. Далее, на каждом шаге
	* позиция энкодера преобразовывается в шаги и если разница оказывается больше
	* CTPMinError, устанавливается флаг STATE_CTP_ERROR и устанавливается состояние ALARM.
	* При управлении ШД с датчиком оборотов (CTP_BASE 1), позиция контролируется по нему.
	* По активному фронту на входе синхронизации контроллер запоминает текущее значение
	* шагов. Далее, при каждом обороте проверяет, на сколько шагов сместились. При
	* рассогласовании более CTPMinError устанавливается флаг STATE_CTP_ERROR и устанавливается состояние ALARM.
	* \endrussian
	* @see set_ctp_settings
	* @see get_ctp_settings
	*/
command "ctp_settings" universal "ctp" (18)
fields:
	int8u CTPMinError				/**< \english Minimum contrast steps from step motor encoder position, wich set STATE_CTP_ERROR flag. Measured in steps step motor. \endenglish \russian Минимальное отличие шагов ШД от положения энкодера, устанавливающее флаг STATE_RT_ERROR. Измеряется в шагах ШД. \endrussian */
	int8u flag CTPFlags of CtpFlags	/**< \english Flags. \endenglish \russian Флаги. \endrussian */
	reserved 10

/** $XIR
	* \english
	* Read UART settings.
	* This function fill structure with UART settings.
	* @see uart_settings_t
	* @param Speed UART speed
	* @param[out] uart_settings UART settings
	* \endenglish
	* \russian
	* Команда чтения настроек UART.
	* Эта функция заполняет структуру настроек UART.
	* @see uart_settings_t
	* @param Speed Cкорость UART
	* @param[out] uart_settings настройки UART
	* \endrussian
	*/
/** $XIW
	* \english
	* Set UART settings.
	* This function send structure with UART settings to controller's memory.
	* @see uart_settings_t
	* @param Speed UART speed
	* @param[in] uart_settings UART settings
	* \endenglish
	* \russian
	*  Команда записи настроек UART.
	* Эта функция записывает структуру настроек UART в память контроллера.
	* @see uart_settings_t
	* @param Speed Cкорость UART
	* @param[in] uart_settings настройки UART
	* \endrussian
	*/
/** $XIS
	* \english
	* UART settings.
	* This structure contains UART settings.
	* \endenglish
	* \russian
	* Настройки UART.
	* Эта структура содержит настройки UART.
	* \endrussian
	* @see get_uart_settings
	* @see set_uart_settings
	*/
command "uart_settings" universal "urt" (16)
fields:
	int32u Speed									/**< \english UART speed \endenglish \russian Cкорость UART \endrussian */
	int16u flag UARTSetupFlags of UARTSetupFlags	/**< \english UART setup flags \endenglish \russian Флаги настройки UART \endrussian */
	reserved 4

/** $XIR
	* \english
	* Read calibration settings.
	* This function fill structure with calibration settings.
	* @see calibration_settings_t
	* @param id an identifier of device
	* @param[out] calibration_settings calibration settings
	* \endenglish
	* \russian
	* Команда чтения калибровочных коэффициентов.
	* Эта функция заполняет структуру калибровочных коэффициентов.
	* @see calibration_settings_t
	* @param id идентификатор устройства
	* @param[out] calibration_settings калибровочные коэффициенты
	* \endrussian
	*/
/** $XIW
	* \english
	* Set calibration settings.
	* This function send structure with calibration settings to controller's memory.
	* @see calibration_settings_t
	* @param id an identifier of device
	* @param[in] calibration_settings calibration settings
	* \endenglish
	* \russian
	* Команда записи калибровочных коэффициентов.
	* Эта функция записывает структуру калибровочных коэффициентов в память контроллера.
	* @see calibration_settings_t
	* @param id идентификатор устройства
	* @param[in] calibration_settings калибровочные коэффициенты
	* \endrussian
	*/
/** $XIS
	* \english
	* Calibration settings.
	* This structure contains calibration settings.
	* \endenglish
	* \russian
	* Калибровочные коэффициенты.
	* Эта структура содержит калибровочные коэффициенты.
	* \endrussian
	* @see get_calibration_settings
	* @see set_calibration_settings
	*/
command "calibration_settings" universal "cal" (118)
fields:
	float CSS1_A              /**< \english Scaling factor for the analogue measurements of the winding A current. \endenglish \russian Коэффициент масштабирования для аналоговых измерений тока в обмотке A. \endrussian */
	float CSS1_B              /**< \english Shift factor for the analogue measurements of the winding A current. \endenglish \russian Коэффициент сдвига для аналоговых измерений тока в обмотке A. \endrussian */
	float CSS2_A              /**< \english Scaling factor for the analogue measurements of the winding B current. \endenglish \russian Коэффициент масштабирования для аналоговых измерений тока в обмотке B. \endrussian */
	float CSS2_B              /**< \english Shift factor for the analogue measurements of the winding B current. \endenglish \russian Коэффициент сдвига для аналоговых измерений тока в обмотке B. \endrussian */
	float FullCurrent_A       /**< \english Scaling factor for the analogue measurements of the full current. \endenglish \russian Коэффициент масштабирования для аналоговых измерений полного тока. \endrussian */
	float FullCurrent_B       /**< \english Shift factor for the analogue measurements of the full current. \endenglish \russian Коэффициент сдвига для аналоговых измерений полного тока. \endrussian */
	reserved 88

/** $XIR
	* \english
	* Read user controller name and flags of setting from FRAM.
	* @param id an identifier of device
	* @param[out] controller_name structure contains previously set user controller name
	* \endenglish
	* \russian
	* Чтение пользовательского имени контроллера и настроек из FRAM.
	* @param id идентификатор устройства
	* @param[out] controller_name структура, содержащая установленное пользовательское имя контроллера и флаги настроек
	* \endrussian
	*/
/** $XIW
	* \english
	* Write user controller name and flags of setting from FRAM.
	* @param id an identifier of device
	* @param[in] controller_name structure contains previously set user controller name
	* \endenglish
	* \russian
	* Запись пользовательского имени контроллера и настроек в FRAM.
	* @param id идентификатор устройства
	* @param[in] controller_information структура, содержащая информацию о контроллере
	* \endrussian
	*/
/** $XIS
	* \english
	* Controller user name and flags of setting.
	* \endenglish
	* \russian
	* Пользовательское имя контроллера и флаги настройки.
	* \endrussian
	*/
command "controller_name" universal "nmf" (30)
fields:
	char ControllerName[16]					/**< \english User conroller name. Can be set by user for his/her convinience. Max string length: 16 chars. \endenglish \russian Пользовательское имя контроллера. Может быть установлено пользователем для его удобства. Максимальная длина строки: 16 символов. \endrussian */
	int8u flag CtrlFlags of ControllerFlags	/**< \english Internal controller settings. \endenglish \russian Настройки контроллера. \endrussian */
	reserved 7

/** $XIR
	* \english
	* Read userdata from FRAM.
	* @param id an identifier of device
	* @param[out] nonvolatile_memory structure contains previously set userdata
	* \endenglish
	* \russian
	* Чтение пользовательских данных из FRAM.
	* @param id идентификатор устройства
	* @param[out] nonvolatile_memory структура, содержащая установленные пользовательские данные
	* \endrussian
	*/
/** $XIW
	* \english
	* Write userdata into FRAM.
	* @param id an identifier of device
	* @param[in] nonvolatile_memory structure contains previously set userdata
	* \endenglish
	* \russian
	* Запись пользовательских данных во FRAM.
	* @param id идентификатор устройства
	* @param[in] nonvolatile_memory структура, содержащая установленные пользовательские данные
	* \endrussian
	*/
/** $XIS
	* \english
	* Userdata for save into FRAM.
	* \endenglish
	* \russian
	* Пользовательские данные для сохранения во FRAM.
	* \endrussian
	*/
command "nonvolatile_memory" universal "nvm" (36)
fields:
	int32u UserData[7]					/**< \english User data. Can be set by user for his/her convinience. Each element of the array stores only 32 bits of user data. This is important on systems where an int type contains more than 4 bytes. For example that all amd64 systems. \endenglish \russian Пользовательские данные. Могут быть установлены пользователем для его удобства. Каждый элемент массива хранит только 32 бита пользовательских данных. Это важно на системах где тип int содержит больше чем 4 байта. Например это все системы amd64.\endrussian */
    reserved 2

//@}

/**
	* \english
	* @name Group of commands movement control
	*
	* \endenglish
	* \russian
	* @name Группа команд управления движением
	*
	* \endrussian
	*/

//@{

/**  $XIW
	* \english
	* Immediately stop the engine, the transition to the STOP, mode
	* key BREAK (winding short-circuited), the regime "retention" is
	* deactivated for DC motors, keeping current in the windings for
	* stepper motors (with Power management settings).
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Немедленная остановка двигателя, переход в состояние STOP,
	* ключи в режиме BREAK (обмотки накоротко замкнуты), режим
	* "удержания" дезактивируется для DC двигателей, удержание тока
	* в обмотках для шаговых двигателей (с учётом Power management
	* настроек).
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_stop" writer "stop" (4)

/** $XIW
	* \english
	* This command adds one element of the FIFO commands that are executed when input clock pulse.
	* Each pulse synchronization or perform that action, which is described in SSNI, if the buffer is empty,
	* or the oldest loaded into the buffer action to temporarily replace the speed and coordinate in SSNI.
	* In the latter case this action is erased from the buffer.
	* The number of remaining empty buffer elements can be found in the structure of GETS.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Это команда добавляет один элемент в буфер FIFO команд,
	* выполняемых при получении входного импульса синхронизации.
	* Каждый импульс синхронизации либо выполнится то действие, которое описано в SSNI,
	* если буфер пуст, либо самое старое из загруженных в буфер действий временно подменяет скорость и координату в SSNI.
	* В последнем случае это действие стирается из буфера.
	* Количество оставшихся пустыми элементов буфера можно узнать в структуре GETS.
	* @param id идентификатор устройства
	* \endrussian
	*/
/** $XIS
	* \english
	* This command adds one element of the FIFO commands.
	* \endenglish
	* \russian
	* Это команда добавляет один элемент в буфер FIFO команд.
	* \endrussian
	*/
command "command_add_sync_in_action" writer "asia" (22)
fields:
	calb float Position							/**< \english Desired position or shift. \endenglish \russian Желаемая позиция или смещение. \endrussian */
	normal int32s Position						/**< \english Desired position or shift (whole steps) \endenglish \russian Желаемая позиция или смещение (целая часть) \endrussian */
	normal int16s uPosition						/**< \english The fractional part of a position or shift in microsteps. Is only used with stepper motor. Range: -255..255. \endenglish \russian Дробная часть позиции или смещения в микрошагах. Используется только с шаговым двигателем. Диапазон: -255..255. \endrussian */
	int32u Time									/**< \english Time for which you want to achieve the desired position in microseconds. \endenglish \russian Время, за которое требуется достичь требуемой позиции, в микросекундах. \endrussian */
	reserved 6

/** $XIW
	* \english
	* Immediately power off motor regardless its state. Shouldn't be used
	* during motion as the motor could be power on again automatically to continue movement.
	* The command is designed for manual motor power off.
	* When automatic power off after stop is required, use power management system.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Немедленное отключение питания двигателя вне зависимости от его состояния.
	* Команда предначена для ручного управления питанием двигателя.
	* Не следует использовать эту команду для отключения двигателя во время движения, так как питание может снова включиться для завершения движения.
	* Для автоматического управления питанием двигателя и его отключении после остановки следует использовать систему управления электропитанием.
	* @param id идентификатор устройства
	* \endrussian
	* @see get_power_settings
	* @see set_power_settings
	*/
command "command_power_off" writer "pwof" (4)

/** $XIW
	* \english
	* Upon receiving the command "move" the engine starts to move with pre-set parameters (speed, acceleration, retention),
	* to the point specified to the Position, uPosition. For stepper motor uPosition
	* sets the microstep, for DC motor this field is not used.
	* @param Position position to move.
	* @param uPosition part of the position to move, microsteps. Range: -255..255.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды "move" двигатель начинает перемещаться (если не используется
	* режим "ТТЛСинхроВхода"), с заранее установленными параметрами (скорость, ускорение,
	* удержание), к точке указанной в полях Position, uPosition. Для шагового мотора
	* uPosition задает значение микрошага, для DC мотора это поле не используется.
	* @param Position заданная позиция.
	* @param uPosition часть позиции в микрошагах. Диапазон: -255..255.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_move" writer "move" (18)
with inline
fields:
	calb float Position			/**< \english Desired position. \endenglish \russian Желаемая позиция. \endrussian */
	normal int32s Position		/**< \english Desired position (whole steps). \endenglish \russian Желаемая позиция (целая часть). \endrussian */
	normal int16s uPosition		/**< \english The fractional part of a position in microsteps. Is only used with stepper motor. Range: -255..255. \endenglish \russian Дробная часть позиции в микрошагах. Используется только с шаговым двигателем. Диапазон: -255..255. \endrussian */
	reserved 6


/** $XIW
	* \english
	* Upon receiving the command "movr" engine starts to move with pre-set parameters (speed, acceleration,
	* hold), left or right (depending on the sign of DeltaPosition) by the number of
	* pulses specified in the fields DeltaPosition, uDeltaPosition. For stepper motor
	* uDeltaPosition sets the microstep, for DC motor this field is not used.
	* @param DeltaPosition shift from initial position.
	* @param uDeltaPosition part of the offset shift, microsteps. Range: -255..255.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды "movr" двигатель начинает смещаться (если не используется
	* режим "ТТЛСинхроВхода"), с заранее установленными параметрами (скорость, ускорение,
	* удержание), влево или вправо (зависит от знака DeltaPosition) на количество
	* импульсов указанное в полях DeltaPosition, uDeltaPosition. Для шагового мотора
	* uDeltaPosition задает значение микрошага, для DC мотора это поле не используется.
	* @param DeltaPosition смещение.
	* @param uDeltaPosition часть смещения в микрошагах. Диапазон: -255..255.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_movr" writer "movr" (18)
with inline
fields:
	calb float DeltaPosition		/**< \english Shift (delta) of position \endenglish \russian Смещение (дельта) позиции \endrussian */
	normal int32s DeltaPosition		/**< \english Shift (delta) of position \endenglish \russian Смещение (дельта) позиции \endrussian */
	normal int16s uDeltaPosition	/**< \english Fractional part of the shift in micro steps is only used with stepper motor. Range: -255..255. \endenglish \russian Дробная часть смещения в микрошагах, используется только с шаговым двигателем. Диапазон: -255..255. \endrussian */
	reserved 6

/** $XIW
	* \english
	* The positive direction is to the right. A value of zero reverses the direction of the
	* direction of the flag, the set speed.
	* Restriction imposed by the trailer, act the same, except that the limit switch contact
	* does not stop. Limit the maximum speed, acceleration and deceleration function.
	* 1) moves the motor according to the speed FastHome, uFastHome and flag HOME_DIR_FAST until
	* limit switch, if the flag is set HOME_STOP_ENDS, until the signal from the input synchronization if
	* the flag HOME_STOP_SYNC (as accurately as possible is important to catch the moment of operation limit switch)
	* or until the signal is received from the speed sensor, if the flag HOME_STOP_REV_SN
	* 2) then moves according to the speed SlowHome, uSlowHome and flag HOME_DIR_SLOW until
	* signal from the clock input, if the flag HOME_MV_SEC. If the flag HOME_MV_SEC reset
	* skip this paragraph.
	* 3) then move the motor according to the speed FastHome, uFastHome and flag HOME_DIR_SLOW a distance
	* HomeDelta, uHomeDelta.
	* description of flags and variable see in description for commands GHOM/SHOM
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Поля скоростей знаковые. Положительное направление это вправо. Нулевое значение флага
	* направления инвертирует направление, заданное скоростью.
	* Ограничение, накладываемые концевиками, действуют так же, за исключением того, что касание
	* концевика не приводит к остановке. Ограничения максимальной скорости, ускорения и замедления действуют.
	* 1) Двигает мотор согласно скоростям FastHome, uFastHome и флагу HOME_DIR_FAST до достижения
	* концевика, если флаг HOME_STOP_ENDS установлен, до достижения сигнала с входа синхронизации, если
	* установлен флаг HOME_STOP_SYNC (важно как можно точнее поймать момент срабатывания концевика)
	* или  до поступления сигнала с датчика оборотов, если установлен флаг HOME_STOP_REV_SN
	* 2) далее двигает согласно скоростям SlowHome, uSlowHome и флагу HOME_DIR_SLOW до достижения
	* сигнала с входа синхронизации, если установлен флаг HOME_MV_SEC. Если флаг HOME_MV_SEC сброшен,
	* пропускаем этот пункт.
	* 3) далее двигает мотор согласно скоростям FastHome, uFastHome и флагу HOME_DIR_SLOW на расстояние
	* HomeDelta, uHomeDelta.
	* Описание флагов и переменных см. описание команд GHOM/SHOM
	* @param id идентификатор устройства
	* \endrussian
	@see home_settings_t
	@see get_home_settings
	@see set_home_settings
	*/
command "command_home" writer "home" (4)

/** $XIW
	* \english
	* Start continous moving to the left.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды "left" двигатель начинает смещаться, с заранее установленными параметрами (скорость, ускорение), влево.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_left" writer "left" (4)

/** $XIW
	* \english
	* Start continous moving to the right.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды "rigt" двигатель начинает смещаться, с заранее установленными параметрами (скорость, ускорение), вправо.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_right" writer "rigt" (4)

/** $XIW
	* \english
	* Upon receiving the command "loft" the engine is shifted from the current
	* point to a distance GENG :: Antiplay, then move to the same point.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды "loft" двигатель смещается из текущей точки на
	* расстояние GENG::Antiplay, затем двигается в ту же точку.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_loft" writer "loft" (4)

/** $XIW
	* \english
	* Soft stop engine. The motor stops with deceleration speed.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Плавная остановка. Двигатель останавливается с ускорением замедления.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_sstp" writer "sstp" (4)

//@}

/**
	* \english
	* @name Group of commands set the current position
	*
	* \endenglish
	* \russian
	* @name Группа команд установки текущей позиции
	*
	* \endrussian
	*/

//@{

/** $XIR
	* \english
	* Reads the value position in steps and micro for stepper motor and encoder steps
	* all engines.
	* @param id an identifier of device
	* @param[out] position structure contains move settings: speed, acceleration, deceleration etc.
	* \endenglish
	* \russian
	* Считывает значение положения в шагах и микрошагах для шагового двигателя и в шагах энкодера
	* всех двигателей.
	* @param id идентификатор устройства
	* @param[out] position структура, содержащая настройки движения: скорость, ускорение, и т.д.
	* \endrussian
	*/
/** $XIS
	* \english
	* Position information.
	* Useful structure that contains position value in steps and micro for stepper motor
	* and encoder steps of all engines.
	* \endenglish
	* \russian
	* Данные о позиции.
	* Структура содержит значение положения в шагах и
	* микрошагах для шагового двигателя и в шагах энкодера всех
	* двигателей.
	* \endrussian
	*/
command "get_position" reader "gpos" (26)
fields:
	calb float Position					/**< \english The position in the engine. \endenglish \russian Позиция двигателя. \endrussian */
	normal int32s Position				/**< \english The position of the whole steps in the engine \endenglish \russian Позиция в основных шагах двигателя \endrussian */
	normal int16s uPosition				/**< \english Microstep position is only used with stepper motors \endenglish \russian Позиция в микрошагах(используется только с шаговыми двигателями). \endrussian */
	int64s EncPosition					/**< \english Encoder position.  \endenglish \russian Позиция энкодера. \endrussian */
	reserved 6

/** $XIW
	* \english
	* Sets any position value in steps and micro for stepper motor
	* and encoder steps of all engines. It means, that changing main
	* indicator of position.
	* @param id an identifier of device
	* @param[out] position structure contains move settings: speed, acceleration, deceleration etc.
	* \endenglish
	* \russian
	* Устанавливает произвольное значение положения в шагах и
	* микрошагах для шагового двигателя и в шагах энкодера всех
	* двигателей. То есть меняется основной показатель положения.
	* @param id идентификатор устройства
	* @param[out] position структура, содержащая настройки движения: скорость, ускорение, и т.д.
	* \endrussian
	*/
/** $XIS
	* \english
	* Position information.
	* Useful structure that contains position value in steps and micro for stepper motor
	* and encoder steps of all engines.
	* \endenglish
	* \russian
	* Данные о позиции.
	* Структура содержит значение положения в шагах и
	* микрошагах для шагового двигателя и в шагах энкодера всех
	* двигателей.
	* \endrussian
	*/
command "set_position" writer "spos" (26)
fields:
	calb float Position						/**< \english The position in the engine. \endenglish \russian Позиция двигателя. \endrussian */
	normal int32s Position					/**< \english The position of the whole steps in the engine \endenglish \russian Позиция в основных шагах двигателя \endrussian */
	normal int16s uPosition					/**< \english Microstep position is only used with stepper motors \endenglish \russian Позиция в микрошагах(используется только с шаговыми двигателями). \endrussian */
	int64s EncPosition						/**< \english Encoder position.  \endenglish \russian Позиция энкодера. \endrussian */
	int8u flag PosFlags of PositionFlags	/**< \english Flags \endenglish \russian Флаги \endrussian */
	reserved 5

/** $XIW
	* \english
	* Sets the current position and the position in which the traffic moves by the move command
	* and movr zero for all cases, except for movement to the target position. In the latter case,
	* set the zero current position and the target position counted so that the absolute position
	* of the destination is the same. That is, if we were at 400 and moved to 500, then the command
	* Zero makes the current position of 0, and the position of the destination - 100. Does not
	* change the mode of movement that is if the motion is carried, it continues, and if the engine
	* is in the "hold", the type of retention remains.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Устанавливает текущую позицию и позицию в которую осуществляется движение по командам
	* move и movr равными нулю для всех случаев, кроме движения к позиции назначения.
	* В последнем случае установить нулём текущую позицию, а позицию назначения пересчитать так,
	* что в абсолютном положении точка назначения не меняется. То есть если мы находились в точке
	* 400 и двигались к 500, то команда Zero делает текущую позицию 0, а позицию назначения - 100.
	* Не изменяет режим движения т.е. если движение осуществлялось, то оно продолжается; если
	* мотор находился в режиме "удержания", то тип удержания сохраняется.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "command_zero" writer "zero" (4)

//@}

/**
	* \english
	* @name Group of commands to save and load settings
	*
	* \endenglish
	* \russian
	* @name Группа команд сохранения и загрузки настроек
	*
	* \endrussian
	*/

//@{

/** $XIW
	* \english
	* Save all settings from controller's RAM to controller's flash memory, replacing previous data in controller's flash memory.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды контроллер выполняет операцию сохранения текущих настроек во встроенную энергонезависимую память контроллера.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "save_settings" writer "save" (4)

/** $XIW
	* \english
	* Read all settings from controller's flash memory to controller's RAM, replacing previous data in controller's RAM.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Чтение всех настроек контроллера из flash памяти в оперативную, заменяя текущие настройки.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "read_settings" writer "read" (4)

/** $XIW
	* \english
	* Save important settings (calibration coefficients and etc.) from controller's RAM to controller's flash memory, replacing previous data in controller's flash memory.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* При получении команды контроллер выполняет операцию сохранения важных настроек (калибровочные коэффициенты и т.п.) во встроенную энергонезависимую память контроллера.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "save_robust_settings" writer "sars" (4)

/** $XIW
	* \english
	* Read important settings (calibration coefficients and etc.) from controller's flash memory to controller's RAM, replacing previous data in controller's RAM.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Чтение важных настроек (калибровочные коэффициенты и т.п.) контроллера из flash памяти в оперативную, заменяя текущие настройки.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "read_robust_settings" writer "rers" (4)

/** $XIW
	* \english
	* Save settings from controller's RAM to stage's EEPROM memory, which spontaneity connected to stage and it isn`t change without it mechanical reconstruction.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Запись настроек контроллера в EEPROM память позиционера, которые непосредственно связаны с позиционером и не меняются без его механической переделки.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "eesave_settings" writer "eesv" (4)

/** $XIW
	* \english
	* Read settings from controller's RAM to stage's EEPROM memory, which spontaneity connected to stage and it isn`t change without it mechanical reconstruction.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Чтение настроек контроллера из EEPROM памяти позиционера, которые непосредственно связаны с позиционером и не меняются без его механической переделки.
	* Эта операция также автоматически выполняется при подключении позиционера с EEPROM памятью. Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "eeread_settings" writer "eerd" (4)

//@}

/**
	* \english
	* @name Group of commands get the status of the controller
	*
	* \endenglish
	* \russian
	* @name Группа команд получения статуса контроллера
	*
	* \endrussian
	*/

//@{

/** $XIR
	* \english
	* Return device state.
	* Useful function that fills structure with snapshot of controller state, including speed, position and boolean flags.
	* @param id an identifier of device
	* @param[out] status structure with snapshot of controller state
	* \endenglish
	* \russian
	* Возвращает информацию о текущем состоянии устройства.
	* @param id идентификатор устройства
	* @param[out] status структура с информацией о текущем состоянии устройства
	* \endrussian
	*/
/** $XIS
	* \english
	* Device state.
	* Useful structure that contains current controller state, including speed, position and boolean flags.
	* \endenglish
	* \russian
	* Состояние устройства.
	* Эта структура содержит основные параметры текущего состоянии контроллера такие как скорость, позиция и флаги состояния.
	* \endrussian
	*/
command "status_impl" reader "gets" (54)
without lock, public
with publicstruct
fields:
	int8u flag MoveSts of MoveState		/**< \english Move state. \endenglish \russian Состояние движения. \endrussian */
	int8u flag MvCmdSts of MvcmdStatus	/**< \english Move command state. \endenglish \russian Состояние команды движения (касается command_move, command_movr, command_left, command_right, command_stop, command_home, command_loft). \endrussian */
	int8u flag PWRSts of PowerState		/**< \english Power state of the stepper motor (used only with stepper motor). \endenglish \russian Состояние питания шагового двигателя (используется только с шаговым двигателем). \endrussian */
	int8u flag EncSts of EncodeStatus	/**< \english Encoder state. \endenglish \russian Состояние энкодера. \endrussian */
	int8u flag WindSts of WindStatus	/**< \english Windings state. \endenglish \russian Состояние обмоток. \endrussian */
	calb float CurPosition				/**< \english Current position. \endenglish \russian Первичное поле, в котором хранится текущая позиция, как бы ни была устроена обратная связь. В случае работы с DC-мотором в этом поле находится текущая позиция по данным с энкодера, в случае работы с ШД-мотором в режиме, когда первичными являются импульсы, подаваемые на мотор. \endrussian */
	normal int32s CurPosition			/**< \english Current position. \endenglish \russian Первичное поле, в котором хранится текущая позиция, как бы ни была устроена обратная связь. В случае работы с DC-мотором в этом поле находится текущая позиция по данным с энкодера, в случае работы с ШД-мотором в режиме, когда первичными являются импульсы, подаваемые на мотор, в этом поле содержится целое значение шагов текущей позиции. \endrussian */
	normal int16s uCurPosition			/**< \english Step motor shaft position in 1/256 microsteps. Used only with stepper motor. \endenglish \russian Дробная часть текущей позиции в микрошагах (-255..255). Используется только с шаговым двигателем. \endrussian */
	int64s EncPosition					/**< \english Current encoder position. \endenglish \russian Текущая позиция по данным с энкодера в импульсах энкодера, используется только если энкодер установлен, активизирован и не является основным датчиком положения, например при использовании энкодера совместно с шаговым двигателем для контроля проскальзования. \endrussian */
	calb float CurSpeed					/**< \english Motor shaft speed. \endenglish \russian Текущая скорость. \endrussian */
	normal int32s CurSpeed				/**< \english Motor shaft speed. \endenglish \russian Текущая скорость. \endrussian */
	normal int16s uCurSpeed				/**< \english Part of motor shaft speed in 1/256 microsteps. Used only with stepper motor. \endenglish \russian Дробная часть текущей скорости в микрошагах (-255..255). Используется только с шаговым двигателем. \endrussian */
	int16s Ipwr							/**< \english Engine current. \endenglish \russian Ток потребления силовой части. \endrussian */
	int16s Upwr							/**< \english Power supply voltage, tens of mV. \endenglish \russian Напряжение на силовой части, десятки мВ. \endrussian */
	int16s Iusb							/**< \english USB current consumption. \endenglish \russian Ток потребления по USB. \endrussian */
	int16s Uusb							/**< \english USB voltage, tens of mV. \endenglish \russian Напряжение на USB, десятки мВ. \endrussian */
	int16s CurT							/**< \english Temperature in tenths of degrees C. \endenglish \russian Температура процессора в десятых долях градусов цельсия. \endrussian */
	int32u flag Flags of StateFlags		/**< \english Set of flags specify motor shaft movement algorithm and list of limitations. \endenglish \russian Флаги состояний. \endrussian */
	int32u flag GPIOFlags of GPIOFlags	/**< \english Set of flags of gpio states \endenglish \russian Флаги состояний GPIO входов. \endrussian */
	int8u CmdBufFreeSpace				/**< \english This field shows the amount of free cells buffer synchronization chain. \endenglish \russian Это поле показывает количество свободных ячеек буфера цепочки синхронизации. \endrussian */
	reserved 4

/** $XIW
  * \english
  * Start measurements and buffering of speed, following error.
  * @param id an identifier of device
  * \endenglish
  * \russian
  * Начать измерения и буферизацию скорости, ошибки следования.
  * @param id идентификатор устройства
  * \endrussian
  */
command "start_measurements" writer "stms" (4)

/** $XIR
  * \english
  * A command to read the data buffer to build a speed graph and a sequence error. Filling the buffer starts with the command "start_measurements".
  * The buffer holds 25 points, the points are taken with a period of 1 ms. To create a robust system, read data every 20 ms,
  * if the buffer is completely full, then it is recommended to repeat the readings every 5 ms until the buffer again becomes filled with 20 points.
  * @see get_measurements_t
  * @param id an identifier of device
  * @param[out] get_measurements structure with buffer and its length.
  * \endenglish
  * \russian
  * Команда чтения буфера данных для построения графиков скорости и ошибки следования. Заполнение буфера начинается по команде "start_measurements".
  * Буффер вмещает 25 точек, точки снимаются с периодом 1 мс. Для создания устойчивой системы следует считывать данные каждые 20 мс, если буффер
  * полностью заполнен, то рекомендуется повторять считывания каждые 5 мс до момента пока буффер вновь не станет заполнен 20-ю точками.
  * @see get_measurements_t
  * @param id идентификатор устройства
  * @param[out] get_measurements структура с буфером и его длинной.
  * \endrussian
  */
/** $XIS
  * \english
  * The buffer holds no more than 25 points. The exact length of the received buffer is reflected in the Length field.
  * \endenglish
  * \russian
  * Буфер вмещает не более 25и точек. Точная длина полученного буффера отражена в поле Length.
  * \endrussian
  * @see measurements
  */
command "measurements" reader "getm" (216)
fields:
  int32s Speed [25]   /**< \english Current speed. \endenglish \russian Текущая скорость. \endrussian */
  int32s Error [25]   /**< \english Current error. \endenglish \russian Текущая скорость. \endrussian */
  int32u Length       /**< \english Length of actual data in buffer. \endenglish \russian Длина фактических данных в буфере. \endrussian */
  reserved 6

/** $XIR
	* \english
	* Return device electrical parameters, useful for charts.
	* Useful function that fill structure with snapshot of controller voltages and currents.
	* @see chart_data_t
	* @param id an identifier of device
	* @param[out] chart_data structure with snapshot of controller parameters.
	* \endenglish
	* \russian
	* Команда чтения состояния обмоток и других не часто используемых данных. Предназначена
	* в первую очередь для получения данных для построения графиков в паре с командой GETS.
	* @see chart_data_t
	* @param id идентификатор устройства
	* @param[out] chart_data структура chart_data.
	* \endrussian
	*/
/** $XIS
	* \english
	* Additional device state.
	* This structure contains additional values such as winding's voltages, currents and temperature.
	* \endenglish
	* \russian
	* Дополнительное состояние устройства.
	* Эта структура содержит основные дополнительные параметры текущего состоянии контроллера, такие напряжения и токи обмоток и температуру.
	* \endrussian
	* @see get_chart_data
	*/
command "chart_data" reader "getc" (38)
fields:
	int16s WindingVoltageA		/**< \english In the case step motor, the voltage across the winding A; in the case of a brushless, the voltage on the first coil, in the case of the only DC. \endenglish \russian В случае ШД, напряжение на обмотке A; в случае бесщеточного, напряжение на первой обмотке; в случае DC на единственной. \endrussian */
	int16s WindingVoltageB		/**< \english In the case step motor, the voltage across the winding B; in case of a brushless, the voltage on the second winding, and in the case of DC is not used. \endenglish \russian В случае ШД, напряжение на обмотке B; в случае бесщеточного, напряжение на второй обмотке; в случае DC не используется. \endrussian */
	int16s WindingVoltageC		/**< \english In the case of a brushless, the voltage on the third winding, in the case step motor and DC is not used. \endenglish \russian В случае бесщеточного, напряжение на третьей обмотке; в случае ШД и DC не используется. \endrussian */
	int16s WindingCurrentA		/**< \english In the case step motor, the current in the coil A; brushless if the current in the first coil, and in the case of a single DC. \endenglish \russian В случае ШД, ток в обмотке A; в случае бесщеточного, ток в первой обмотке; в случае DC в единственной. \endrussian */
	int16s WindingCurrentB		/**< \english In the case step motor, the current in the coil B; brushless if the current in the second coil, and in the case of DC is not used. \endenglish \russian В случае ШД, ток в обмотке B; в случае бесщеточного, ток в второй обмотке; в случае DC не используется. \endrussian */
	int16s WindingCurrentC		/**< \english In the case of a brushless, the current in the third winding, in the case step motor and DC is not used. \endenglish \russian В случае бесщеточного, ток в третьей обмотке; в случае ШД и DC не используется. \endrussian */
	int16u Pot			/**< \english Analog input value in ten-thousandths. Range: 0..10000 \endenglish \russian Значение на аналоговом входе. Диапазон: 0..10000 \endrussian */
	int16u Joy			/**< \english The joystick position in the ten-thousandths. Range: 0..10000 \endenglish \russian Положение джойстика в десятитысячных долях. Диапазон: 0..10000 \endrussian */
	int16s DutyCycle			/**< \english Duty cycle of PWM. \endenglish \russian Коэффициент заполнения ШИМ. \endrussian */
	reserved 14

/** $XIR
	* \english
	* Return device information. It's available from the firmware and bootloader.
	* @param id an identifier of device
	* @param[out] device_information device information
	* \endenglish
	* \russian
	* Возвращает информацию об устройстве. Доступна как из прошивки, так и из бутлоадера.
	* @param id идентификатор устройства.
	* @param[out] device_information информация об устройстве
	* \endrussian
	*/
/** $XIS
	* \english
	* Read command controller information.
	* The controller responds to this command in any state. Manufacturer field for all XI**
	* devices should contain the string "XIMC" (validation is performed on it)
	* The remaining fields contain information about the device.
	* \endenglish
	* \russian
	* Команда чтения информации о контроллере.
	* Контроллер отвечает на эту команду в любом состоянии. Поле Manufacturer для всех XI**
	* девайсов должно содержать строку "XIMC" (по нему производится валидация).
	* Остальные поля содержат информацию об устройстве.
	* \endrussian
	* @see get_device_information
	*/
command "device_information_impl" reader "geti" (36)
without lock, public
with dualsync, publicstruct
fields:
	char Manufacturer[4]		/**< \english Manufacturer \endenglish \russian Производитель \endrussian */
	char ManufacturerId[2]		/**< \english Manufacturer id \endenglish \russian Идентификатор производителя \endrussian */
	char ProductDescription[8]	/**< \english Product description \endenglish \russian Описание продукта \endrussian */
	int8u Major					/**< \english The major number of the hardware version. \endenglish \russian Основной номер версии железа. \endrussian */
	int8u Minor					/**< \english Minor number of the hardware version. \endenglish \russian Второстепенный номер версии железа. \endrussian */
	int16u Release				/**< \english Number of edits this release of hardware. \endenglish \russian Номер правок этой версии железа. \endrussian */
	reserved 12

/** $XIR
	* \english
	* Read device serial number.
	* @param id an identifier of device
	* @param[out] serial serial number
	* \endenglish
	* \russian
	* Чтение серийного номера контроллера.
	* @param id идентификатор устройства
	* @param[out] SerialNumber серийный номер контроллера
	* \endrussian
	*/
command "serial_number" reader "gser" (10)
with inline
fields:
	int32u SerialNumber		/**< \english Board serial number. \endenglish \russian Серийный номер платы. \endrussian */

//@}

/**
	* \english
	* @name Group of commands to work with the controller firmware
	*
	* \endenglish
	* \russian
	* @name Группа команд для работы с прошивкой контроллера
	*
	* \endrussian
	*/

//@{

/** $XIR
	* \english
	* Read controller's firmware version.
	* @param id an identifier of device
	* @param[out] Major major version
	* @param[out] Minor minor version
	* @param[out] Release release version
	* \endenglish
	* \russian
	* Чтение номера версии прошивки контроллера.
	* @param id идентификатор устройства
	* @param[out] Major номер основной версии
	* @param[out] Minor номер дополнительной версии
	* @param[out] Release номер релиза
	* \endrussian
	*/
command "firmware_version" reader "gfwv" (10)
with inline
fields:
	int8u Major		/**< \english Firmware major version number \endenglish \russian Мажорный номер версии прошивки \endrussian */
	int8u Minor		/**< \english Firmware minor version number \endenglish \russian Минорный номер версии прошивки \endrussian */
	int16u Release	/**< \english Firmware release version number \endenglish \russian Номер релиза версии прошивки \endrussian */

/** $XIW
	* \english
	* Command puts the controller to update the firmware.
	* After receiving this command, the firmware board sets a flag (for loader), sends echo reply and restarts the controller.
	* \endenglish
	* \russian
	* Команда переводит контроллер в режим обновления прошивки.
	* Получив такую команду, прошивка платы устанавливает флаг (для загрузчика), отправляет эхо-ответ и перезагружает контроллер.
	* \endrussian
	*/
command "service_command_updf" writer "updf" (4)
without crc, lock

//@}

/**
	* \english
	* @name Service commands
	*
	* \endenglish
	* \russian
	* @name Группа сервисных команд
	*
	* \endrussian
	*/

//@{

/** $XIW
	* \english
	* Write device serial number and hardware version to controller's flash memory.
	* Along with the new serial number and hardware version a "Key" is transmitted.
	* The SN and hardware version are changed and saved when keys match.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] serial number structure contains new serial number and secret key.
	* \endenglish
	* \russian
	* Запись серийного номера и версии железа во flash память контроллера.
	* Вместе с новым серийным номером и версией железа передаётся "Ключ",
	* только при совпадении которого происходит изменение и сохранение.
	* Функция используется только производителем.
	* @param id идентификатор устройства
	* @param[in] serial number структура, содержащая серийный номер, версию железа и ключ.
	* \endrussian
	*/
/**  $XIS
	* \english
	* Serial number structure and hardware version.
	* The structure keep new serial number, hardware version and valid key.
	* The SN and hardware version are changed and saved when transmitted key matches stored key.
	* Can be used by manufacturer only.
	* \endenglish
	* \russian
	* Структура с серийным номером и версией железа.
	* Вместе с новым серийным номером и версией железа передаётся "Ключ",
	* только при совпадении которого происходит изменение и сохранение.
	* Функция используется только производителем.
	* \endrussian
	*/
command "serial_number" writer "sser" (50)
fields:
	int32u SN		/**< \english New board serial number. \endenglish \russian Новый серийный номер платы. \endrussian */
	byte Key[32]	/**< \english Protection key (256 bit). \endenglish \russian Ключ защиты для установки серийного номера (256 бит). \endrussian */
	int8u Major		/**< \english The major number of the hardware version. \endenglish \russian Основной номер версии железа. \endrussian */
	int8u Minor		/**< \english Minor number of the hardware version. \endenglish \russian Второстепенный номер версии железа. \endrussian */
	int16u Release	/**< \english Number of edits this release of hardware. \endenglish \russian Номер правок этой версии железа. \endrussian */
	reserved 4

/** $XIR
	* \english
	* Read analog data structure that contains raw analog data from ADC embedded on board.
	* This function used for device testing and deep recalibraton by manufacturer only.
	* @param id an identifier of device
	* @param[out] analog_data analog data coefficients
	* \endenglish
	* \russian
	* Чтение аналоговых данных, содержащих данные с АЦП и нормированные значения величин.
	* Эта функция используется для тестирования и калибровки устройства.
	* @param id идентификатор устройства
	* @param[out] analog_data аналоговые данные
	* \endrussian
	*/
/** $XIS
	* \english
	* Analog data.
	* This structure contains raw analog data from ADC embedded on board.
	* These data used for device testing and deep recalibraton by manufacturer only.
	* \endenglish
	* \russian
	* Аналоговые данные.
	* Эта структура содержит необработанные данные с АЦП и нормированные значения.
	* Эти данные используются в сервисных целях для тестирования и калибровки устройства.
	* \endrussian
	* @see get_analog_data
	*/
command "analog_data" reader "rdan" (76)
fields:
	int16u A1Voltage_ADC	/**< \english "Voltage on pin 1 winding A" raw data from ADC. \endenglish \russian "Выходное напряжение на 1 выводе обмотки А" необработанные данные с АЦП. \endrussian */
	int16u A2Voltage_ADC	/**< \english "Voltage on pin 2 winding A" raw data from ADC. \endenglish \russian "Выходное напряжение на 2 выводе обмотки А" необработанные данные с АЦП. \endrussian */
	int16u B1Voltage_ADC	/**< \english "Voltage on pin 1 winding B" raw data from ADC. \endenglish \russian "Выходное напряжение на 1 выводе обмотки B" необработанные данные с АЦП. \endrussian */
	int16u B2Voltage_ADC	/**< \english "Voltage on pin 2 winding B" raw data from ADC. \endenglish \russian "Выходное напряжение на 2 выводе обмотки B" необработанные данные с АЦП. \endrussian */
	int16u SupVoltage_ADC	/**< \english "Voltage on the top of MOSFET full bridge" raw data from ADC. \endenglish \russian "Напряжение питания ключей Н-моста" необработанные данные с АЦП. \endrussian */
	int16u ACurrent_ADC		/**< \english "Winding A current" raw data from ADC. \endenglish \russian "Ток через обмотку А" необработанные данные с АЦП. \endrussian */
	int16u BCurrent_ADC		/**< \english "Winding B current" raw data from ADC. \endenglish \russian "Ток через обмотку B" необработанные данные с АЦП. \endrussian */
	int16u FullCurrent_ADC	/**< \english "Full current" raw data from ADC. \endenglish \russian "Полный ток" необработанные данные с АЦП. \endrussian */
	int16u Temp_ADC			/**< \english Voltage from temperature sensor, raw data from ADC. \endenglish \russian Напряжение с датчика температуры, необработанные данные с АЦП. \endrussian */
	int16u Joy_ADC			/**< \english Joystick raw data from ADC. \endenglish \russian Джойстик, необработанные данные с АЦП. \endrussian */
	int16u Pot_ADC			/**< \english Voltage on analog input, raw data from ADC \endenglish \russian Напряжение на аналоговом входе, необработанные данные с АЦП \endrussian */
	int16u L5_ADC			/**< \english USB supply voltage after the current sense resistor, from ADC. \endenglish \russian Напряжение питания USB после current sense резистора, необработанные данные с АЦП. \endrussian */
	int16u H5_ADC			/**< \english Power supply USB from ADC \endenglish \russian Напряжение питания USB, необработанные данные с АЦП \endrussian */
	int16s A1Voltage		/**< \english "Voltage on pin 1 winding A" calibrated data. \endenglish \russian "Выходное напряжение на 1 выводе обмотки А" откалиброванные данные. \endrussian */
	int16s A2Voltage		/**< \english "Voltage on pin 2 winding A" calibrated data. \endenglish \russian "Выходное напряжение на 2 выводе обмотки А" откалиброванные данные. \endrussian */
	int16s B1Voltage		/**< \english "Voltage on pin 1 winding B" calibrated data. \endenglish \russian "Выходное напряжение на 1 выводе обмотки B" откалиброванные данные. \endrussian */
	int16s B2Voltage		/**< \english "Voltage on pin 2 winding B" calibrated data. \endenglish \russian "Выходное напряжение на 2 выводе обмотки B" откалиброванные данные. \endrussian */
	int16s SupVoltage		/**< \english "Voltage on the top of MOSFET full bridge" calibrated data. \endenglish \russian "Напряжение питания ключей Н-моста" откалиброванные данные. \endrussian */
	int16s ACurrent			/**< \english "Winding A current" calibrated data. \endenglish \russian "Ток через обмотку А" откалиброванные данные. \endrussian */
	int16s BCurrent			/**< \english "Winding B current" calibrated data. \endenglish \russian "Ток через обмотку B" откалиброванные данные. \endrussian */
	int16s FullCurrent		/**< \english "Full current" calibrated data. \endenglish \russian "Полный ток" откалиброванные данные. \endrussian */
	int16s Temp				/**< \english Temperature, calibrated data. \endenglish \russian Температура, откалиброванные данные. \endrussian */
	int16s Joy				/**< \english Joystick, calibrated data. Range: 0..10000 \endenglish \russian Джойстик во внутренних единицах. Диапазон: 0..10000 \endrussian */
	int16s Pot				/**< \english Analog input, calibrated data. Range: 0..10000 \endenglish \russian Аналоговый вход во внутренних единицах. Диапазон: 0..10000 \endrussian */
	int16s L5				/**< \english USB supply voltage after the current sense resistor. \endenglish \russian Напряжение питания USB после current sense резистора \endrussian */
	int16s H5				/**< \english Power supply USB \endenglish \russian Напряжение питания USB \endrussian */
	int16u deprecated
	int32s R				/**< \english Motor winding resistance in mOhms(is only used with stepper motor). \endenglish \russian Сопротивление обмоток двигателя(для шагового двигателя),  в мОм \endrussian */
	int32s L				/**< \english Motor winding pseudo inductance in uHn(is only used with stepper motor). \endenglish \russian Псевдоиндуктивность обмоток двигателя(для шагового двигателя),  в мкГн \endrussian */
	reserved 8

/** $XIR
	* \english
	* Read data from firmware for debug purpose.
	* Its use depends on context, firmware version and previous history.
	* @param id an identifier of device
	* @param[out] debug_read Debug data.
	* \endenglish
	* \russian
	* Чтение данных из прошивки для отладки и поиска неисправностей.
	* Получаемые данные зависят от версии прошивки, истории и контекста использования.
	* @param id идентификатор устройства
	* @param[out] debug_read Данные для отладки.
	* \endrussian
	*/
/** $XIS
	* \english
	* Debug data.
	* These data are used for device debugging by manufacturer only.
	* \endenglish
	* \russian
	* Отладочные данные.
	* Эти данные используются в сервисных целях для тестирования и отладки устройства.
	* \endrussian
	*/
command "debug_read" reader "dbgr" (142)
fields:
	byte DebugData[128]		/**< \english Arbitrary debug data. \endenglish \russian Отладочные данные. \endrussian */
	reserved 8

/** $XIW
	* \english
	* Write data to firmware for debug purpose.
	* @param id an identifier of device
	* @param[in] debug_write Debug data.
	* \endenglish
	* \russian
	* Запись данных в прошивку для отладки и поиска неисправностей.
	* @param id идентификатор устройства
	* @param[in] debug_write Данные для отладки.
	* \endrussian
	*/
/** $XIS
	* \english
	* Debug data.
	* These data are used for device debugging by manufacturer only.
	* \endenglish
	* \russian
	* Отладочные данные.
	* Эти данные используются в сервисных целях для тестирования и отладки устройства.
	* \endrussian
	*/
command "debug_write" writer "dbgw" (142)
fields:
	byte DebugData[128]		/**< \english Arbitrary debug data. \endenglish \russian Отладочные данные. \endrussian */
	reserved 8

/** $XIW
	* \english
	* The command for clear controller FRAM.
	* The memory is cleared by filling the whole memory byte 0x00.
	* After cleaning, the controller restarts.
	* No response to this command.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Команда очистки FRAM контроллера.
	* Память очищается путем заполнения всего объема памяти байтами 0x00.
	* После очистки контроллер перезагружается. Ответа на эту команду нет.
	* @param id идентификатор устройства
	* \endrussian
	*/
command "service_command_clear_fram_impl" writer "clfr" (4) reader "clfr" (0)
without answer, public, crc

//@}

/**
	* \english
	* @name Group of commands to work with EEPROM
	*
	* \endenglish
	* \russian
	* @name Группа команд работы с EEPROM подвижки
	*
	* \endrussian
	*/

//@{

/** $XIR
	* \english
	* Read user stage name from EEPROM.
	* @param id an identifier of device
	* @param[out] stage_name structure contains previously set user stage name
	* \endenglish
	* \russian
	* Чтение пользовательского имени подвижки из EEPROM.
	* @param id идентификатор устройства
	* @param[out] stage_name структура, содержащая установленное пользовательское имя позиционера
	* \endrussian
	*/
/** $XIW
	* \english
	* Write user stage name from EEPROM.
	* @param id an identifier of device
	* @param[in] stage_name structure contains previously set user stage name
	* \endenglish
	* \russian
	* Запись пользовательского имени подвижки в EEPROM.
	* @param id идентификатор устройства
	* @param[in] stage_name структура, содержащая установленное пользовательское имя позиционера
	* \endrussian
	*/
/** $XIS
	* \english
	* Stage user name.
	* \endenglish
	* \russian
	* Пользовательское имя подвижки.
	* \endrussian
	*/
command "stage_name" universal "nme" (30)
fields:
	char PositionerName[16]			/**< \english User positioner name. Can be set by user for his/her convinience. Max string length: 16 chars. \endenglish \russian Пользовательское имя подвижки. Может быть установлено пользователем для его удобства. Максимальная длина строки: 16 символов. \endrussian */
	reserved 8

/** $XIR
	* \english
	* Read stage information from EEPROM.
	* @param id an identifier of device
	* @param[out] stage_information structure contains stage information
	* \endenglish
	* \russian
	* Чтение информации о позиционере из EEPROM.
	* @param id идентификатор устройства
	* @param[out] stage_information структура, содержащая информацию о позиционере
	* \endrussian
	*/
/** $XIW
	* \english
	* Set stage information to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] stage_information structure contains stage information
	* \endenglish
	* \russian
	* Запись информации о позиционере в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] stage_information структура, содержащая информацию о позиционере
	* \endrussian
	*/
/** $XIS
	* \english
	* Stage information.
	* \endenglish
	* \russian
	* Информация о позиционере.
	* \endrussian
	* @see set_stage_information
	* @see get_stage_information
	*/
command "stage_information" universal "sti" (70)
fields:
	char Manufacturer[16]			/**< \english Manufacturer. Max string length: 16 chars. \endenglish \russian Производитель. Максимальная длина строки: 16 символов. \endrussian */
	char PartNumber[24]				/**< \english Series and PartNumber. Max string length: 24 chars. \endenglish \russian Серия и номер модели. Максимальная длина строки: 24 символа. \endrussian */	
	reserved 24

/** $XIR 
	* \english
	* Read stage settings from EEPROM.
	* @param id an identifier of device
	* @param[out] stage_settings structure contains stage settings
	* \endenglish
	* \russian
	* Чтение настроек позиционера из EEPROM.
	* @param id идентификатор устройства
	* @param[out] stage_settings структура, содержащая настройки позиционера
	* \endrussian
	*/
/** $XIW
	* \english
	* Set stage settings to EEPROM.
	* Can be used by manufacturer only
	* @param id an identifier of device
	* @param[in] stage_settings structure contains stage settings
	* \endenglish
	* \russian
	* Запись настроек позиционера в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] stage_settings структура, содержащая настройки позиционера
	* \endrussian
	*/
/** $XIS
	* \english
	* Stage settings.
	* \endenglish
	* \russian
	* Настройки позиционера.
	* \endrussian
	* @see set_stage_settings
	* @see get_stage_settings
	*/
command "stage_settings" universal "sts" (70)
fields:
	float LeadScrewPitch			/**< \english Lead screw pitch (mm). Data type: float. \endenglish \russian Шаг ходового винта в мм. Тип данных: float. \endrussian */	
	char Units[8]					/**< \english Units for MaxSpeed and TravelRange fields of the structure (steps, degrees, mm, ...). Max string length: 8 chars. \endenglish \russian Единицы измерения расстояния, используемые в полях MaxSpeed и TravelRange (шаги, градусы, мм, ...), Максимальная длина строки: 8 символов. \endrussian */	
	float MaxSpeed					/**< \english Max speed (Units/c). Data type: float. \endenglish \russian Максимальная скорость (Units/с). Тип данных: float. \endrussian */	
	float TravelRange				/**< \english Travel range (Units). Data type: float. \endenglish \russian Диапазон перемещения (Units). Тип данных: float. \endrussian */	
	float SupplyVoltageMin			/**< \english Supply voltage minimum (V). Data type: float. \endenglish \russian Минимальное напряжение питания (В). Тип данных: float. \endrussian */	
	float SupplyVoltageMax			/**< \english Supply voltage maximum (V). Data type: float. \endenglish \russian Максимальное напряжение питания (В). Тип данных: float. \endrussian */	
	float MaxCurrentConsumption		/**< \english Max current consumption (A). Data type: float. \endenglish \russian Максимальный ток потребления (А). Тип данных: float. \endrussian */	
	float HorizontalLoadCapacity	/**< \english Horizontal load capacity (kg). Data type: float. \endenglish \russian Горизонтальная грузоподъемность (кг). Тип данных: float. \endrussian */	
	float VerticalLoadCapacity		/**< \english Vertical load capacity (kg). Data type: float. \endenglish \russian Вертикальная грузоподъемность (кг). Тип данных: float. \endrussian */	
	reserved 24	
	
/** $XIR 
	* \english
	* Read motor information from EEPROM.
	* @param id an identifier of device
	* @param[out] motor_information structure contains motor information
	* \endenglish
	* \russian
	* Чтение информации о двигателе из EEPROM.
	* @param id идентификатор устройства
	* @param[out] motor_information структура, содержащая информацию о двигателе
	* \endrussian
	*/
/** $XIW
	* \english
	* Set motor information to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] motor_information structure contains motor information
	* \endenglish
	* \russian
	* Запись информации о двигателе в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] motor_information структура, содержащая информацию о двигателе
	* \endrussian
	*/
/** $XIS
	* \english
	* motor information.
	* \endenglish
	* \russian
	* Информация о двигателе.
	* \endrussian
	* @see set_motor_information
	* @see get_motor_information
	*/
command "motor_information" universal "mti" (70)
fields:
	char Manufacturer[16]			/**< \english Manufacturer. Max string length: 16 chars. \endenglish \russian Производитель. Максимальная длина строки: 16 символов. \endrussian */	
	char PartNumber[24]				/**< \english Series and PartNumber. Max string length: 24 chars. \endenglish \russian Серия и номер модели. Максимальная длина строки: 24 символа. \endrussian */	
	reserved 24

/** $XIR 
	* \english
	* Read motor settings from EEPROM.
	* @param id an identifier of device
	* @param[out] motor_settings structure contains motor settings
	* \endenglish
	* \russian
	* Чтение настроек двигателя из EEPROM.
	* @param id идентификатор устройства
	* @param[out] motor_settings структура, содержащая настройки двигателя
	* \endrussian
	*/
/** $XIW
	* \english
	* Set motor settings to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] motor_settings structure contains motor information
	* \endenglish
	* \russian
	* Запись настроек двигателя в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] motor_settings структура, содержащая настройки двигателя
	* \endrussian
	*/
/** $XIS
	* \english
	* Physical characteristics and limitations of the motor.
	* \endenglish
	* \russian
	* Физический характеристики и ограничения мотора.
	* \endrussian
	* @see set_motor_settings
	* @see get_motor_settings
	*/
command "motor_settings" universal "mts" (112)
fields:
	int8u flag MotorType of MotorTypeFlags	/**< \english Motor type \endenglish \russian Тип двигателя \endrussian */
	int8u ReservedField						/**< \english Reserved \endenglish \russian Зарезервировано \endrussian */
	int16u Poles							/**< \english Number of pole pairs for DC or BLDC motors or number of steps per rotation for stepper motor. \endenglish \russian Кол-во пар полюсов у DС или BLDC двигателя или кол-во шагов на оборот для шагового двигателя. \endrussian */
	int16u Phases							/**< \english Number of phases for BLDC motors. \endenglish \russian Кол-во фаз у BLDC двигателя. \endrussian */
	float NominalVoltage					/**< \english Nominal voltage on winding (B). Data type: float \endenglish \russian Номинальное напряжение на обмотке (В). Тип данных: float. \endrussian */
	float NominalCurrent					/**< \english Maximum direct current in winding for DC and BLDC engines, nominal current in windings for stepper motor (A). Data type: float.  \endenglish \russian Максимальный постоянный ток в обмотке для DC и BLDC двигателей, номинальный ток в обмотке для шаговых двигателей (А). Тип данных: float. \endrussian */
	float NominalSpeed						/**< \english Not used. Nominal speed(rpm). Used for DC and BLDC engine. Data type: float. \endenglish \russian Не используется. Номинальная скорость (об/мин). Применяется для DC и BLDC двигателей. Тип данных: float. \endrussian */
	float NominalTorque						/**< \english Nominal torque(mN m). Used for DC and BLDC engine. Data type: float. \endenglish \russian Номинальный крутящий момент (мН м). Применяется для DC и BLDC двигателей. Тип данных: float. \endrussian */
	float NominalPower						/**< \english Nominal power(W). Used for DC and BLDC engine. Data type: float. \endenglish \russian Номинальная мощность(Вт). Применяется для DC и BLDC двигателей. Тип данных: float. \endrussian */	
	float WindingResistance					/**< \english Resistance of windings for DC engine, each of two windings for stepper motor or each of there windings for BLDC engine(Ohm). Data type: float.\endenglish \russian Сопротивление обмотки DC двигателя, каждой из двух обмоток шагового двигателя или каждой из трёх обмоток BLDC двигателя (Ом). Тип данных: float. \endrussian */
	float WindingInductance					/**< \english Inductance of windings for DC engine, each of two windings for stepper motor or each of there windings for BLDC engine(mH). Data type: float.\endenglish \russian Индуктивность обмотки DC двигателя, каждой из двух обмоток шагового двигателя или каждой из трёх обмоток BLDC двигателя (мГн). Тип данных: float. \endrussian */
	float RotorInertia						/**< \english Rotor inertia(g cm2). Data type: float.\endenglish \russian Инерция ротора (г cм2). Тип данных: float. \endrussian */
	float StallTorque						/**< \english Torque hold position for a stepper motor or torque at a motionless rotor for other types of engines (mN m). Data type: float. \endenglish \russian Крутящий момент удержания позиции для шагового двигателя или крутящий момент при неподвижном роторе для других типов двигателей (мН м). Тип данных: float. \endrussian */
	float DetentTorque						/**< \english Holding torque position with un-powered coils (mN m). Data type: float. \endenglish \russian Момент удержания позиции с незапитанными обмотками (мН м). Тип данных: float. \endrussian */
	float TorqueConstant					/**< \english Torque constant, which determines the aspect ratio of maximum moment of force from the rotor current flowing in the coil (mN m / A). Used mainly for DC motors. Data type: float. \endenglish \russian Константа крутящего момента, определяющая коэффициент пропорциональности максимального момента силы ротора от протекающего в обмотке тока (мН м/А). Используется в основном для DC двигателей. Тип данных: float. \endrussian */
	float SpeedConstant						/**< \english Velocity constant, which determines the value or amplitude of the induced voltage on the motion of DC or BLDC motor (rpm / V) or stepper motor (steps/s / V). Data type: float. \endenglish \russian Константа скорости, определяющая значение или амплитуду напряжения наведённой индукции при вращении ротора DC или BLDC двигателя (об/мин / В) или шагового двигателя (шаг/с / В). Тип данных: float. \endrussian */
	float SpeedTorqueGradient				/**< \english Speed torque gradient (rpm / mN m). Data type: float. \endenglish \russian Градиент крутящего момента (об/мин / мН м). Тип данных: float. \endrussian */
	float MechanicalTimeConstant			/**< \english Mechanical time constant (ms). Data type: float. \endenglish \russian Механическая постоянная времени (мс). Тип данных: float. \endrussian */
	float MaxSpeed							/**< \english The maximum speed for stepper motors (steps/s) or DC and BLDC motors (rmp). Data type: float. \endenglish \russian Максимальная разрешённая скорость для шаговых двигателей (шаг/с) или для DC и BLDC двигателей (об/мин). Тип данных: float. \endrussian */
	float MaxCurrent						/**< \english The maximum current in the winding (A). Data type: float. \endenglish \russian Максимальный ток в обмотке (А). Тип данных: float. \endrussian */
	float MaxCurrentTime					/**< \english Safe duration of overcurrent in the winding (ms). Data type: float. \endenglish \russian Безопасная длительность максимального тока в обмотке (мс). Тип данных: float. \endrussian */
	float NoLoadCurrent						/**< \english The current consumption in idle mode (A). Used for DC and BLDC motors. Data type: float. \endenglish \russian Ток потребления в холостом режиме (А). Применяется для DC и BLDC двигателей. Тип данных: float. \endrussian */
	float NoLoadSpeed						/**< \english Idle speed (rpm). Used for DC and BLDC motors. Data type: float. \endenglish \russian Скорость в холостом режиме (об/мин). Применяется для DC и BLDC двигателей. Тип данных: float. \endrussian */
	reserved 24

/** $XIR
	* \english
	* Read encoder information from EEPROM.
	* @param id an identifier of device
	* @param[out] encoder_information structure contains information about encoder
	* \endenglish
	* \russian
	* Чтение информации об энкодере из EEPROM.
	* @param id идентификатор устройства
	* @param[out] encoder_information структура, содержащая информацию об энкодере
	* \endrussian
	*/
/** $XIW
	* \english
	* Set encoder information to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] encoder_information structure contains information about encoder
	* \endenglish
	* \russian
	* Запись информации об энкодере в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] encoder_information структура, содержащая информацию об энкодере
	* \endrussian
	*/
/** $XIS
	* \english
	* Encoder information.
	* \endenglish
	* \russian
	* Информация об энкодере.
	* \endrussian
	* @see set_encoder_information
	* @see get_encoder_information
	*/
command "encoder_information" universal "eni" (70)
fields:
	char Manufacturer[16]			/**< \english Manufacturer. Max string length: 16 chars. \endenglish \russian Производитель. Максимальная длина строки: 16 символов. \endrussian */	
	char PartNumber[24]				/**< \english Series and PartNumber. Max string length: 24 chars. \endenglish \russian Серия и номер модели. Максимальная длина строки: 24 символа. \endrussian */	
	reserved 24

/** $XIR
	* \english
	* Read encoder settings from EEPROM.
	* @param id an identifier of device
	* @param[out] encoder_settings structure contains encoder settings
	* \endenglish
	* \russian
	* Чтение настроек энкодера из EEPROM.
	* @param id идентификатор устройства
	* @param[out] encoder_settings структура, содержащая настройки энкодера
	* \endrussian
	*/
/** $XIW
	* \english
	* Set encoder settings to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] encoder_settings structure contains encoder settings
	* \endenglish
	* \russian
	* Запись настроек энкодера в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] encoder_settings структура, содержащая настройки энкодера
	* \endrussian
	*/
/** $XIS
	* \english
	* Encoder settings.
	* \endenglish
	* \russian
	* Настройки энкодера.
	* \endrussian
	* @see set_encoder_settings
	* @see get_encoder_settings
	*/
command "encoder_settings" universal "ens" (54)
fields:
	float MaxOperatingFrequency		/**< \english Max operation frequency (kHz). Data type: float. \endenglish \russian Максимальная частота (кГц). Тип данных: float. \endrussian */
	float SupplyVoltageMin			/**< \english Minimum supply voltage (V). Data type: float. \endenglish \russian Минимальное напряжение питания (В). Тип данных: float. \endrussian */
	float SupplyVoltageMax			/**< \english Maximum supply voltage (V). Data type: float. \endenglish \russian Максимальное напряжение питания (В). Тип данных: float. \endrussian */
	float MaxCurrentConsumption		/**< \english Max current consumption (mA). Data type: float. \endenglish \russian Максимальное потребление тока (мА). Тип данных: float. \endrussian */
	int32u PPR						/**< \english The number of counts per revolution \endenglish \russian Количество отсчётов на оборот \endrussian */
	int32u flag EncoderSettings of EncoderSettingsFlags /**< \english Encoder settings flags \endenglish \russian Флаги настроек энкодера \endrussian */
	reserved 24

/** $XIR
	* \english
	* Read hall sensor information from EEPROM.
	* @param id an identifier of device
	* @param[out] hallsensor_information structure contains information about hall sensor
	* \endenglish
	* \russian
	* Чтение информации о датчиках Холла из EEPROM.
	* @param id идентификатор устройства
	* @param[out] hallsensor_information структура, содержащая информацию о датчиках Холла
	* \endrussian
	*/
/** $XIW
	* \english
	* Set hall sensor information to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] hallsensor_information structure contains information about hall sensor
	* \endenglish
	* \russian
	* Запись информации о датчиках Холла в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] hallsensor_information структура, содержащая информацию о датчиках Холла
	* \endrussian
	*/
/** $XIS
	* \english
	* Hall sensor information.
	* \endenglish
	* \russian
	* Информация о датчиках Холла.
	* \endrussian
	* @see set_hallsensor_information
	* @see get_hallsensor_information
	*/
command "hallsensor_information" universal "hsi" (70)
fields:
	char Manufacturer[16]			/**< \english Manufacturer. Max string length: 16 chars. \endenglish \russian Производитель. Максимальная длина строки: 16 символов. \endrussian */	
	char PartNumber[24]				/**< \english Series and PartNumber. Max string length: 24 chars. \endenglish \russian Серия и номер модели. Максимальная длина строки: 24 символа. \endrussian */	
	reserved 24

/** $XIR
	* \english
	* Read hall sensor settings from EEPROM.
	* @param id an identifier of device
	* @param[out] hallsensor_settings structure contains hall sensor settings
	* \endenglish
	* \russian
	* Чтение настроек датчиков Холла из EEPROM.
	* @param id идентификатор устройства
	* @param[out] hallsensor_settings структура, содержащая настройки датчиков Холла
	* \endrussian
	*/
/** $XIW
	* \english
	* Set hall sensor settings to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] hallsensor_settings structure contains hall sensor settings
	* \endenglish
	* \russian
	* Запись настроек датчиков Холла в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] hallsensor_settings структура, содержащая настройки датчиков Холла
	* \endrussian
	*/
/** $XIS
	* \english
	* Hall sensor settings.
	* \endenglish
	* \russian
	* Настройки датчиков Холла.
	* \endrussian
	* @see set_hallsensor_settings
	* @see get_hallsensor_settings
	*/
command "hallsensor_settings" universal "hss" (50)
fields:
	float MaxOperatingFrequency		/**< \english Max operation frequency (kHz). Data type: float. \endenglish \russian Максимальная частота (кГц). Тип данных: float. \endrussian */
	float SupplyVoltageMin			/**< \english Minimum supply voltage (V). Data type: float. \endenglish \russian Минимальное напряжение питания (В). Тип данных: float. \endrussian */
	float SupplyVoltageMax			/**< \english Maximum supply voltage (V). Data type: float. \endenglish \russian Максимальное напряжение питания (В). Тип данных: float. \endrussian */
	float MaxCurrentConsumption		/**< \english Max current consumption (mA). Data type: float. \endenglish \russian Максимальное потребление тока (мА). Тип данных: float. \endrussian */
	int32u PPR						/**< \english The number of counts per revolution \endenglish \russian Количество отсчётов на оборот \endrussian */
	reserved 24	
	
/** $XIR
	* \english
	* Read gear information from EEPROM.
	* @param id an identifier of device
	* @param[out] gear_information structure contains information about step gearhead
	* \endenglish
	* \russian
	* Чтение информации о редукторе из EEPROM.
	* @param id идентификатор устройства
	* @param[out] gear_information структура, содержащая информацию о редукторе
	* \endrussian
	*/
/** $XIW
	* \english
	* Set gear information to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] gear_information structure contains information about step gearhead
	* \endenglish
	* \russian
	* Запись информации о редукторе в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] gear_information структура, содержащая информацию о редукторе
	* \endrussian
	*/
/** $XIS
	* \english
	* Gear information.
	* \endenglish
	* \russian
	* Информация о редукторе.
	* \endrussian
	* @see set_gear_information
	* @see get_gear_information
	*/
command "gear_information" universal "gri" (70)
fields:
	char Manufacturer[16]			/**< \english Manufacturer. Max string length: 16 chars. \endenglish \russian Производитель. Максимальная длина строки: 16 символов. \endrussian */	
	char PartNumber[24]				/**< \english Series and PartNumber. Max string length: 24 chars. \endenglish \russian Серия и номер модели. Максимальная длина строки: 24 символа. \endrussian */	
	reserved 24

/** $XIR
	* \english
	* Read gear settings from EEPROM.
	* @param id an identifier of device
	* @param[out] gear_settings structure contains step gearhead settings
	* \endenglish
	* \russian
	* Чтение настроек редуктора из EEPROM.
	* @param id идентификатор устройства
	* @param[out] gear_settings структура, содержащая настройки редуктора
	* \endrussian
	*/
/** $XIW
	* \english
	* Set gear settings to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] gear_settings structure contains step gearhead settings
	* \endenglish
	* \russian
	* Запись настроек редуктора в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] gear_settings структура, содержащая настройки редуктора
	* \endrussian
	*/
/** $XIS
	* \english
	* Gear setings.
	* \endenglish
	* \russian
	* Настройки редуктора.
	* \endrussian
	* @see set_gear_settings
	* @see get_gear_settings
	*/
command "gear_settings" universal "grs" (58)
fields:
	float ReductionIn			/**< \english Input reduction coefficient. (Output = (ReductionOut / ReductionIn) * Input) Data type: float. \endenglish \russian Входной коэффициент редуктора. (Выход = (ReductionOut/ReductionIn) * вход) Тип данных: float. \endrussian */
	float ReductionOut			/**< \english Output reduction coefficient. (Output = (ReductionOut / ReductionIn) * Input) Data type: float. \endenglish \russian Выходной коэффициент редуктора. (Выход = (ReductionOut/ReductionIn) * вход) Тип данных: float. \endrussian */
	float RatedInputTorque		/**< \english Max continuous torque (N m). Data type: float. \endenglish \russian Максимальный крутящий момент (Н м). Тип данных: float. \endrussian */
	float RatedInputSpeed		/**< \english Max speed on the input shaft (rpm). Data type: float. \endenglish \russian Максимальная скорость на входном валу редуктора (об/мин). Тип данных: float. \endrussian */
	float MaxOutputBacklash		/**< \english Output backlash of the reduction gear(degree). Data type: float. \endenglish \russian Выходной люфт редуктора (градус). Тип данных: float.\endrussian */
	float InputInertia			/**< \english Equivalent input gear inertia (g cm2). Data type: float. \endenglish \russian Эквивалентная входная инерция редуктора(г см2). Тип данных: float. \endrussian */
	float Efficiency			/**< \english Reduction gear efficiency (%). Data type: float. \endenglish \russian КПД редуктора (%). Тип данных: float. \endrussian */
	reserved 24

/** $XIR
	* \english
	* Read additional accessories information from EEPROM.
	* @param id an identifier of device
	* @param[out] accessories_settings structure contains information about additional accessories
	* \endenglish
	* \russian
	* Чтение информации о дополнительных аксессуарах из EEPROM.
	* @param id идентификатор устройства
	* @param[out] accessories_settings структура, содержащая информацию о дополнительных аксессуарах
	* \endrussian
	*/
/** $XIW
	* \english
	* Set additional accessories information to EEPROM.
	* Can be used by manufacturer only.
	* @param id an identifier of device
	* @param[in] accessories_settings structure contains information about additional accessories
	* \endenglish
	* \russian
	* Запись информации о дополнительных аксессуарах в EEPROM.
	* Функция должна использоваться только производителем.
	* @param id идентификатор устройства
	* @param[in] accessories_settings структура, содержащая информацию о дополнительных аксессуарах
	* \endrussian
	*/
/** $XIS
	* \english
	* Additional accessories information.
	* \endenglish
	* \russian
	* Информация о дополнительных аксессуарах.
	* \endrussian
	* @see set_accessories_settings
	* @see get_accessories_settings
	*/
	
command "accessories_settings" universal "acc" (114)
fields:
	char MagneticBrakeInfo[24]		/**< \english The manufacturer and the part number of magnetic brake, the maximum string length is 24 characters. \endenglish \russian Производитель и номер магнитного тормоза, Максимальная длина строки: 24 символов. \endrussian */ 
	float MBRatedVoltage			/**< \english Rated voltage for controlling the magnetic brake (B). Data type: float. \endenglish \russian Номинальное напряжение для управления магнитным тормозом (В). Тип данных: float. \endrussian */
	float MBRatedCurrent			/**< \english Rated current for controlling the magnetic brake (A). Data type: float. \endenglish \russian Номинальный ток для управления магнитным тормозом (А). Тип данных: float. \endrussian */ 
	float MBTorque					/**< \english Retention moment (mN m). Data type: float. \endenglish \russian Удерживающий момент (мН м). Тип данных: float. \endrussian */ 
	int32u flag MBSettings of MBSettingsFlags 	/**< \english Flags of magnetic brake settings \endenglish \russian Флаги настроек магнитного тормоза. \endrussian */ 
	char TemperatureSensorInfo[24]	/**< \english The manufacturer and the part number of the temperature sensor, the maximum string length: 24 characters. \endenglish \russian Производитель и номер температурного датчика, Максимальная длина строки: 24 символов. \endrussian */ 
	float TSMin						/**< \english The minimum measured temperature (degrees Celsius) Data type: float. \endenglish \russian Минимальная измеряемая температура (град Цельсия). Тип данных: float. \endrussian */ 
	float TSMax						/**< \english The maximum measured temperature (degrees Celsius) Data type: float. \endenglish \russian Максимальная измеряемая температура (град Цельсия) Тип данных: float. \endrussian */ 
	float TSGrad					/**< \english The temperature gradient (V/degrees Celsius). Data type: float. \endenglish \russian Температурный градиент (В/град Цельсия). Тип данных: float. \endrussian */ 
	int32u flag TSSettings of TSSettingsFlags 	/**< \english Flags of temperature sensor settings. \endenglish \russian Флаги настроек температурного датчика. \endrussian */ 
	int32u flag LimitSwitchesSettings of LSFlags	/**< \english Flags of limit switches settings. \endenglish \russian Флаги настроек концевиков. \endrussian */ 
	reserved 24	
	
//@}
/**
	* \english
	* @name Bootloader commands
	*
	* \endenglish
	* \russian
	* @name Команды загрузчика
	*
	* \endrussian
	*/

//@{

/** $XIR
	* \english
	* Read controller's firmware version.
	* @param id an identifier of device
	* @param[out] Major major version
	* @param[out] Minor minor version
	* @param[out] Release release version
	* \endenglish
	* \russian
	* Чтение номера версии прошивки контроллера.
	* @param id идентификатор устройства
	* @param[out] Major номер основной версии
	* @param[out] Minor номер дополнительной версии
	* @param[out] Release номер релиза
	* \endrussian
	*/
command "bootloader_version" reader "gblv" (10)
with inline
fields:
	int8u Major		/**< \english Bootloader major version number \endenglish \russian Мажорный номер версии загрузчика \endrussian */
	int8u Minor		/**< \english Bootloader minor version number \endenglish \russian Минорный номер версии загрузчика \endrussian */
	int16u Release	/**< \english Bootloader release version number \endenglish \russian Номер релиза версии загрузчика \endrussian */

/** $XIW
		* \english
		* Command initiates the transfer of control to firmware. This command is
		* also available from the firmware for compatibility.
		* Result = RESULT_OK, if the transition from the loader in the firmware is
		* possible. After the response to this command is executed transition.
		* Result = RESULT_NO_FIRMWARE, if the firmware is not found.
		* Result = RESULT_ALREADY_IN_FIRMWARE, if this command is called from the firmware.
		* @param id an identifier of device
		* @param[out] sresult command result
		* \endenglish
		* \russian
		* Команда инициирует передачу управления прошивке. Эта команда так же доступна из прошивки,
		* для совместимости.
		* Result = RESULT_OK, если переход из загрузчика в прошивку возможен. После ответа на эту
		* команду выполняется переход.
		* Result = RESULT_NO_FIRMWARE, если прошивка не найдена.
		* Result = RESULT_ALREADY_IN_FIRMWARE, если эта команда была вызвана из прошивки.
		* @param id идентификатор устройства
		* @param[out] sresult результат выполнения команды
		* \endrussian
*/
command "service_command_goto_firmware_impl" writer "gofw" (4) reader "gofw" (15)
with inline
without public, crc
answer:
	int8u serviceanswer sresult	/**< \english Result of command. \endenglish \russian Результат выполнения команды. \endrussian */
	reserved 8

/** $XIR
	* \english
	* Read random number from controller.
	* @param id an identifier of device
	* @param[out] random sequence generated by the controller
	* \endenglish
	* \russian
	* Чтение случайного числа из контроллера.
	* @param id идентификатор устройства
	* @param[out] случайная последовательность, сгенерированная контроллером
	* \endrussian
	*/
/** $XIS
	* \english
	* Random key.
	* Structure that contains random key used in encryption of WKEY and SSER command contents.
	* \endenglish
	* \russian
	* Случайный ключ.
	* Структура которая содержит случайный ключ, использующийся для шифрования содержимого команд WKEY и SSER.
	* \endrussian
	*/
command "init_random" reader "irnd" (24)
with public
fields:
	byte key[16] /**< \english Random key. \endenglish \russian Случайный ключ. \endrussian */
	reserved 2

/** $XIR
  * \english
  * This value is unique to each individual die but is not a random value.
  * This unique device identifier can be used to initiate secure boot processes
  * or as a serial number for USB or other end applications.
  * @param id an identifier of device
  * @param[out] the result of fields 0-3 concatenated defines the unique 128-bit device identifier.
  * \endenglish
  * \russian
  * Считывает уникальный идентификатор каждого чипа, это значение не является случайным.
  * Уникальный идентификатор может быть использован в качестве инициализационного вектора
  * для операций шифрования бутлоадера или в качестве серийного номера для USB и других применений.
  * @param id идентификатор устройства
  * @param[out] результат полей 0-3 определяет уникальный 128-битный идентификатор.
  * \endrussian
  */
/** $XIS
  * \english
  * Globally unique identifier.
  * \endenglish
  * \russian
  * Глобальный уникальный идентификатор.
  * \endrussian
  */
command "globally_unique_identifier" reader "guid" (40)
with public
fields:
  int32u UniqueID0 /**< \english Unique ID 0. \endenglish \russian Уникальный ID 0. \endrussian */
  int32u UniqueID1 /**< \english Unique ID 1. \endenglish \russian Уникальный ID 1. \endrussian */
  int32u UniqueID2 /**< \english Unique ID 2. \endenglish \russian Уникальный ID 2. \endrussian */
  int32u UniqueID3 /**< \english Unique ID 3. \endenglish \russian Уникальный ID 3. \endrussian */
  reserved 18

/** $XIR
	* \english
	* Check for firmware on device.
	* Result = RESULT_NO_FIRMWARE, if the firmware is not found.
	* Result = RESULT_HAS_FIRMWARE, if the firmware found.
	* @param name a name of device
	* @param[out] ret non-zero if firmware existed
	* \endenglish
	* \russian
	* Команда определяет наличие в контроллере ПО.
	* Данная команда доступна так же из прошивки.
	* Result = RESULT_NO_FIRMWARE, если прошивка не найдена.
	* Result = RESULT_HAS_FIRMWARE, если прошивка найдена.
	* @param name имя устройства
	* @param[out] ret не ноль, если прошивка присутствует
	* \endrussian
	*/
command "service_command_has_firmware_impl" writer "hasf" (4) reader "hasf" (15)
with inline
without public, crc
answer:
	int8u serviceanswer sresult	/**< \english Result of command. \endenglish \russian Результат выполнения команды. \endrussian */
	reserved 8

/** $XIW
	* \english
	* Write command key to decrypt the firmware.
	* Result = RESULT_OK, if the command loader.
	* Result = RESULT_HARD_ERROR, if at the time of the command there was mistake.
	* Result not available using the library write_key, the field value is processed by the function.
	* Can be used by manufacturer only.
	* @param Name a name of device
	* @param[in] Key protection key.
	* \endenglish
	* \russian
	* Команда записи ключа для расшифровки прошивки.
	* Result = RESULT_OK, если команда выполнена загрузчиком.
	* Result = RESULT_HARD_ERROR, если во время выполнения команды произошла ошибка.
	* Result не доступен через функцию библиотеки write_key, значение поля обрабатывается внутри функции.
	* Функция используется только производителем.
	* @param Name имя устройства
	* @param[in] Key ключ защиты.
	* \endrussian
	*/
command "service_command_write_key_impl" writer "wkey" (46) reader "wkey" (15)
with inline
without public
fields:
	byte Key[32]	/**< \english Protection key (256 bit). \endenglish \russian Ключ защиты (256 бит). \endrussian */
	reserved 8
answer:
	int8u serviceresult sresult	/**< \english Result of command. \endenglish \russian Результат выполнения команды. \endrussian */
	reserved 8

/** $XIR
	* \english
	* Command to open a session ISP (in-system programming) when downloading the firmware.
	* Result = RESULT_OK, if the command loader.
	* Result = RESULT_SOFT_ERROR, if at the time of the command error occurred.
	* Result not available using the library command_update_firmware,
	* the field value is processed by the function.
	* @param name a name of device
	* @param[out] ret non-zero if the command loader.
	* \endenglish
	* \russian
	* Команда служит для открытия сеанса ISP (in-system programming) при загрузке прошивки.
	* Result = RESULT_OK, если команда выполнена загрузчиком.
	* Result = RESULT_SOFT_ERROR, если во время выполнения команды произошла ошибка.
	* Result не доступен через функцию библиотеки command_update_firmware, значение
	* поля обрабатывается внутри функции.
	* @param name имя устройства
	* @param[out] ret не ноль, если команда выполнена загрузчиком.
	* \endrussian
	*/
command "service_command_connect_impl" writer "conn" (14) reader "conn" (15)
without public
with inline
fields:
	reserved 8
answer:
	int8u serviceresult sresult	/**< \english Result of command. \endenglish \russian Результат выполнения команды. \endrussian */
	reserved 8

/** $XIR
	* \english
	* Command to close the session ISP (in-system programming) when loading firmware.
	* Result = RESULT_OK, if the command loader.
	* Result = RESULT_HARD_ERROR, if at the time of the command hardware error occurred.
	* Result = RESULT_SOFT_ERROR, if at the time of the command software error occurred.
	* Result not available using the library command_update_firmware,
	* the field value is processed by the function.
	* @param name a name of device
	* @param[out] ret non-zero if the command loader.
	* \endenglish
	* \russian
	* Команда служит для закрытия сеанса ISP (in-system programming) при загрузке прошивки.
	* Result = RESULT_OK, если команда выполнена загрузчиком.
	* Result = RESULT_HARD_ERROR, если во время выполнения команды произошла аппаратная ошибка.
	* Result = RESULT_SOFT_ERROR, если во время выполнения команды произошла программная ошибка.
	* Result не доступен через функцию библиотеки command_update_firmware,
	* значение поля обрабатывается внутри функции.
	* @param name имя устройства
	* @param[out] ret не ноль, если команда выполнена загрузчиком.
	* \endrussian
	*/
command "service_command_disconnect_impl" writer "disc" (14) reader "disc" (15)
with inline
without public
fields:
	reserved 8
answer:
	int8u serviceresult sresult	/**< \english Result of command. \endenglish \russian Результат выполнения команды. \endrussian */
	reserved 8

/** $XIW
	* \english
	* Writes encoded firmware in the controller flash memory.
	* Result of each packet write is not available. Overall result is available when firmware upload is finished.
	* @param[in] Data[128] Encoded firmware
	* \endenglish
	* \russian
	* Записывает данные (прошивку) во Flash память контроллера.
	* Не возвращает результат выполнения, хотя может завершаться ошибкой.
	* Ошибочность заливки и тип ошибки можно узнать при завершении заливки.
	* @param[in] Data[128] Закодированная прошивка
	* \endrussian
	*/
command "service_command_write_data_impl" writer "wdat" (142) reader "wdat" (4)
without public
with inline
fields:
	byte Data[128]	metalen	/**< \english Encoded firmware. \endenglish \russian Закодированная прошивка. \endrussian */
	reserved 8

/** $XIW
	* \english
	* The reset command controller and go into bootloader mode,
	* for compatibility with the exchange protocol to the loader.
	* No response to this command.
	* \endenglish
	* \russian
	* Команда сброса контроллера и перехода в режим загрузчика, добавлена для
	* совместимости с Протоколом Обмена Загрузчика. Ответа на эту команду нет.
	* \endrussian
	*/
command "service_command_reset_impl" writer "rest" (4) reader "rest" (0)
without answer, public, crc

/** $XIW
	* \english
	* Change motor - command for switching output relay.
	* @param id an identifier of device
	* \endenglish
	* \russian
	* Сменить двигатель - команда для переключения выходного реле.
        * @param id идентификатор устройства
	* \endrussian
	*/
/** $XIS
        * \english
        * Change motor - command for switching output relay.
        * \endenglish
        * \russian
        * Сменить двигатель - команда для переключения выходного реле.
        * \endrussian
        */
command "command_change_motor" writer "chmt" (22)
fields:
	int8u Motor /**< \english Motor number which it should be switch relay on [0..1] \endenglish \russian Номер мотора, на который следует переключить реле [0..1] \endrussian */
	reserved 15

//@}


/**
	* \english
	* @name Service functions
	* Functions are intended for deep controller setup.
	* There is no necessity to use it during normal operation.
	* These functions have to be used by skilled engineers only.
	* If you want to use it please consult with the manufacturer.
	* Wrong usage lead to device malfunction, can lead to irreversible damage of board.
	* \endenglish
	* \russian
	* @name Сервисные функции
	* Эти функции необходимы для начального конфигурирования, тестирования и обновления устройства.
	* Не применяйте их при обычной работе с контроллером.
	* При необходимости, проконсультируйтесь пожалуйста с производителем.
	* Неправильное использование этих функций может привести к неработоспособности устройства.
	* \endrussian
	*/























/** vim: set ft=xi ts=4 sw=4: */
