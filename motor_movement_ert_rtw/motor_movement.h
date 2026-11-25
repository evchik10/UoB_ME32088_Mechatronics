/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: motor_movement.h
 *
 * Code generated for Simulink model 'motor_movement'.
 *
 * Model version                  : 1.2
 * Simulink Coder version         : 25.2 (R2025b) 28-Jul-2025
 * C/C++ source code generated on : Wed Nov 25 17:36:57 2026
 *
 * Target selection: ert.tlc
 * Embedded hardware selection: ARM Compatible->ARM Cortex-A (32-bit)
 * Code generation objectives: Unspecified
 * Validation result: Not run
 */

#ifndef motor_movement_h_
#define motor_movement_h_
#ifndef motor_movement_COMMON_INCLUDES_
#define motor_movement_COMMON_INCLUDES_
#include "rtwtypes.h"
#include "rtw_extmode.h"
#include "sysran_types.h"
#include "MW_gpio.h"
#include "MW_pigs.h"
#include "MW_TCPSendReceive.h"
#endif                                 /* motor_movement_COMMON_INCLUDES_ */

#include "motor_movement_types.h"
#include <stddef.h>

/* Macros for accessing real-time model data structure */
#ifndef rtmGetFinalTime
#define rtmGetFinalTime(rtm)           ((rtm)->Timing.tFinal)
#endif

#ifndef rtmGetRTWExtModeInfo
#define rtmGetRTWExtModeInfo(rtm)      ((rtm)->extModeInfo)
#endif

#ifndef rtmGetErrorStatus
#define rtmGetErrorStatus(rtm)         ((rtm)->errorStatus)
#endif

#ifndef rtmSetErrorStatus
#define rtmSetErrorStatus(rtm, val)    ((rtm)->errorStatus = (val))
#endif

#ifndef rtmGetStopRequested
#define rtmGetStopRequested(rtm)       ((rtm)->Timing.stopRequestedFlag)
#endif

#ifndef rtmSetStopRequested
#define rtmSetStopRequested(rtm, val)  ((rtm)->Timing.stopRequestedFlag = (val))
#endif

#ifndef rtmGetStopRequestedPtr
#define rtmGetStopRequestedPtr(rtm)    (&((rtm)->Timing.stopRequestedFlag))
#endif

#ifndef rtmGetT
#define rtmGetT(rtm)                   ((rtm)->Timing.taskTime0)
#endif

#ifndef rtmGetTFinal
#define rtmGetTFinal(rtm)              ((rtm)->Timing.tFinal)
#endif

#ifndef rtmGetTPtr
#define rtmGetTPtr(rtm)                (&(rtm)->Timing.taskTime0)
#endif

/* Block signals (default storage) */
typedef struct {
  uint8_T TCPIPReceive_o1;             /* '<Root>/TCP//IP Receive' */
  int8_T TCPIPReceive_o2;              /* '<Root>/TCP//IP Receive' */
  boolean_T GPIORead;                  /* '<Root>/GPIO Read' */
} B_motor_movement_T;

/* Block states (default storage) for system '<Root>' */
typedef struct {
  raspi_internal_PWMBlock_motor_T obj; /* '<Root>/Step Pin' */
  codertarget_raspi_internal_jp_T obj_n;/* '<Root>/TCP//IP Receive' */
  codertarget_raspi_internal_Ra_T obj_j;/* '<Root>/Enable Pin' */
  codertarget_raspi_internal_Ra_T obj_h;/* '<Root>/Direction Pin' */
  codertarget_raspi_internal__j_T obj_b;/* '<Root>/GPIO Read' */
  struct {
    void *LoggedData;
  } Scope_PWORK;                       /* '<Root>/Scope' */

  uint32_T is_c1_motor_movement;       /* '<Root>/Chart1' */
  uint16_T temporalCounter_i1;         /* '<Root>/Chart1' */
  uint8_T is_active_c1_motor_movement; /* '<Root>/Chart1' */
} DW_motor_movement_T;

/* Parameters (default storage) */
struct P_motor_movement_T_ {
  real_T DC_Value;                     /* Expression: 0.5
                                        * Referenced by: '<Root>/DC'
                                        */
};

/* Real-time Model Data Structure */
struct tag_RTM_motor_movement_T {
  const char_T *errorStatus;
  RTWExtModeInfo *extModeInfo;

  /*
   * Sizes:
   * The following substructure contains sizes information
   * for many of the model attributes such as inputs, outputs,
   * dwork, sample times, etc.
   */
  struct {
    uint32_T checksums[4];
  } Sizes;

  /*
   * SpecialInfo:
   * The following substructure contains special information
   * related to other components that are dependent on RTW.
   */
  struct {
    const void *mappingInfo;
  } SpecialInfo;

  /*
   * Timing:
   * The following substructure contains information regarding
   * the timing information for the model.
   */
  struct {
    time_T taskTime0;
    uint32_T clockTick0;
    time_T stepSize0;
    time_T tFinal;
    boolean_T stopRequestedFlag;
  } Timing;
};

/* Block parameters (default storage) */
extern P_motor_movement_T motor_movement_P;

/* Block signals (default storage) */
extern B_motor_movement_T motor_movement_B;

/* Block states (default storage) */
extern DW_motor_movement_T motor_movement_DW;

/* Model entry point functions */
extern void motor_movement_initialize(void);
extern void motor_movement_step(void);
extern void motor_movement_terminate(void);

/* Real-time Model object */
extern RT_MODEL_motor_movement_T *const motor_movement_M;
extern volatile boolean_T stopRequested;
extern volatile boolean_T runModel;

/*-
 * The generated code includes comments that allow you to trace directly
 * back to the appropriate location in the model.  The basic format
 * is <system>/block_name, where system is the system number (uniquely
 * assigned by Simulink) and block_name is the name of the block.
 *
 * Use the MATLAB hilite_system command to trace the generated code back
 * to the model.  For example,
 *
 * hilite_system('<S3>')    - opens system 3
 * hilite_system('<S3>/Kp') - opens and selects block Kp which resides in S3
 *
 * Here is the system hierarchy for this model
 *
 * '<Root>' : 'motor_movement'
 * '<S1>'   : 'motor_movement/Chart1'
 */
#endif                                 /* motor_movement_h_ */

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
