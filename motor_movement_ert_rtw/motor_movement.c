/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: motor_movement.c
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

#include "motor_movement.h"
#include "motor_movement_types.h"
#include "rtwtypes.h"
#include "motor_movement_private.h"
#include <math.h>

/* Named constants for Chart: '<Root>/Chart1' */
#define motor_movement_IN_Backward     (1U)
#define motor_movement_IN_Forward      (2U)
#define motor_movement_IN_Off          (3U)
#define motor_movement_IN_Start        (4U)

/* Block signals (default storage) */
B_motor_movement_T motor_movement_B;

/* Block states (default storage) */
DW_motor_movement_T motor_movement_DW;

/* Real-time model */
static RT_MODEL_motor_movement_T motor_movement_M_;
RT_MODEL_motor_movement_T *const motor_movement_M = &motor_movement_M_;

/* Forward declaration for local functions */
static void motor_movement_SystemCore_setup(codertarget_raspi_internal_jp_T *obj);
real_T rt_roundd_snf(real_T u)
{
  real_T y;
  if (fabs(u) < 4.503599627370496E+15) {
    if (u >= 0.5) {
      y = floor(u + 0.5);
    } else if (u > -0.5) {
      y = u * 0.0;
    } else {
      y = ceil(u - 0.5);
    }
  } else {
    y = u;
  }

  return y;
}

static void motor_movement_SystemCore_setup(codertarget_raspi_internal_jp_T *obj)
{
  real_T tmp;
  int32_T i;
  int16_T errorNo;
  uint16_T tmp_0;
  char_T ipaddr[7];
  uint8_T isLittleEndian;
  static const char_T ipaddr_0[7] = "Server";

  /* Start for MATLABSystem: '<Root>/TCP//IP Receive' */
  obj->isInitialized = 1;
  obj->isServer_ = 1.0;
  for (i = 0; i < 7; i++) {
    ipaddr[i] = ipaddr_0[i];
  }

  /* Start for MATLABSystem: '<Root>/TCP//IP Receive' */
  tmp = rt_roundd_snf(obj->isServer_);
  if (tmp < 65536.0) {
    if (tmp >= 0.0) {
      tmp_0 = (uint16_T)tmp;
    } else {
      tmp_0 = 0U;
    }
  } else {
    tmp_0 = MAX_uint16_T;
  }

  /* Start for MATLABSystem: '<Root>/TCP//IP Receive' */
  TCPStreamSetup(25000, 0, &obj->connStream_, tmp_0, 0.0, &errorNo, &ipaddr[0]);
  littleEndianCheck(&isLittleEndian);
}

/* Model step function */
void motor_movement_step(void)
{
  real_T y;
  int32_T direction;
  int32_T enable;
  int16_T errorNo;
  uint16_T tmp;

  /* MATLABSystem: '<Root>/GPIO Read' */
  EXT_GPIO_read(23U, &motor_movement_B.GPIORead);

  /* MATLABSystem: '<Root>/TCP//IP Receive' */
  y = rt_roundd_snf(motor_movement_DW.obj_n.isServer_);
  if (y < 65536.0) {
    if (y >= 0.0) {
      tmp = (uint16_T)y;
    } else {
      tmp = 0U;
    }
  } else {
    tmp = MAX_uint16_T;
  }

  /* MATLABSystem: '<Root>/TCP//IP Receive' */
  TCPStreamStepRecv(&motor_movement_B.TCPIPReceive_o1,
                    &motor_movement_B.TCPIPReceive_o2, 1,
                    motor_movement_DW.obj_n.connStream_, &errorNo, tmp);

  /* Chart: '<Root>/Chart1' */
  if (motor_movement_DW.temporalCounter_i1 < 511) {
    motor_movement_DW.temporalCounter_i1++;
  }

  if (motor_movement_DW.is_active_c1_motor_movement == 0) {
    motor_movement_DW.is_active_c1_motor_movement = 1U;
    motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Start;
    enable = 1;
    direction = 0;
  } else {
    switch (motor_movement_DW.is_c1_motor_movement) {
     case motor_movement_IN_Backward:
      enable = 0;
      direction = 1;
      if (motor_movement_DW.temporalCounter_i1 >= 480) {
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Forward;
        direction = 0;
      } else if ((motor_movement_B.TCPIPReceive_o2 == 1) &&
                 (motor_movement_B.TCPIPReceive_o1 == 0)) {
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Start;
        enable = 1;
        direction = 0;
      }
      break;

     case motor_movement_IN_Forward:
      enable = 0;
      direction = 0;
      if (!motor_movement_B.GPIORead) {
        motor_movement_DW.temporalCounter_i1 = 0U;
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Off;
        enable = 1;
        direction = 1;
      } else if ((motor_movement_B.TCPIPReceive_o2 == 1) &&
                 (motor_movement_B.TCPIPReceive_o1 == 0)) {
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Start;
        enable = 1;
      }
      break;

     case motor_movement_IN_Off:
      enable = 1;
      direction = 1;
      if (motor_movement_DW.temporalCounter_i1 >= 200) {
        motor_movement_DW.temporalCounter_i1 = 0U;
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Backward;
        enable = 0;
      } else if ((motor_movement_B.TCPIPReceive_o2 == 1) &&
                 (motor_movement_B.TCPIPReceive_o1 == 0)) {
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Start;
        direction = 0;
      }
      break;

     default:
      /* case IN_Start: */
      enable = 1;
      direction = 0;
      if (motor_movement_B.GPIORead && (motor_movement_B.TCPIPReceive_o1 == 1) &&
          (motor_movement_B.TCPIPReceive_o2 == 1)) {
        motor_movement_DW.is_c1_motor_movement = motor_movement_IN_Forward;
        enable = 0;
      }
      break;
    }
  }

  /* End of Chart: '<Root>/Chart1' */

  /* MATLABSystem: '<Root>/Direction Pin' */
  EXT_GPIO_write(18U, (uint8_T)direction);

  /* MATLABSystem: '<Root>/Enable Pin' */
  EXT_GPIO_write(17U, (uint8_T)enable);

  /* Start for MATLABSystem: '<Root>/Step Pin' incorporates:
   *  Constant: '<Root>/DC'
   */
  if (motor_movement_P.DC_Value <= 1.0) {
    y = motor_movement_P.DC_Value;
  } else {
    y = 1.0;
  }

  if (!(y >= 0.0)) {
    y = 0.0;
  }

  /* MATLABSystem: '<Root>/Step Pin' */
  EXT_PWMBlock_setDutyCycle(motor_movement_DW.obj.PinNumber, y);

  /* Update absolute time for base rate */
  /* The "clockTick0" counts the number of times the code of this task has
   * been executed. The absolute time is the multiplication of "clockTick0"
   * and "Timing.stepSize0". Size of "clockTick0" ensures timer will not
   * overflow during the application lifespan selected.
   */
  motor_movement_M->Timing.taskTime0 =
    ((time_T)(++motor_movement_M->Timing.clockTick0)) *
    motor_movement_M->Timing.stepSize0;
}

/* Model initialize function */
void motor_movement_initialize(void)
{
  /* Registration code */
  rtmSetTFinal(motor_movement_M, -1);
  motor_movement_M->Timing.stepSize0 = 0.01;

  /* External mode info */
  motor_movement_M->Sizes.checksums[0] = (1312765066U);
  motor_movement_M->Sizes.checksums[1] = (1358027081U);
  motor_movement_M->Sizes.checksums[2] = (2136559987U);
  motor_movement_M->Sizes.checksums[3] = (461294739U);

  {
    static const sysRanDType rtAlwaysEnabled = SUBSYS_RAN_BC_ENABLE;
    static RTWExtModeInfo rt_ExtModeInfo;
    static const sysRanDType *systemRan[7];
    motor_movement_M->extModeInfo = (&rt_ExtModeInfo);
    rteiSetSubSystemActiveVectorAddresses(&rt_ExtModeInfo, systemRan);
    systemRan[0] = &rtAlwaysEnabled;
    systemRan[1] = &rtAlwaysEnabled;
    systemRan[2] = &rtAlwaysEnabled;
    systemRan[3] = &rtAlwaysEnabled;
    systemRan[4] = &rtAlwaysEnabled;
    systemRan[5] = &rtAlwaysEnabled;
    systemRan[6] = &rtAlwaysEnabled;
    rteiSetModelMappingInfoPtr(motor_movement_M->extModeInfo,
      &motor_movement_M->SpecialInfo.mappingInfo);
    rteiSetChecksumsPtr(motor_movement_M->extModeInfo,
                        motor_movement_M->Sizes.checksums);
    rteiSetTPtr(motor_movement_M->extModeInfo, rtmGetTPtr(motor_movement_M));
  }

  {
    int32_T ret;
    char_T b[45];
    static const char_T b_0[45] =
      "Unable to configure pin %u for PWM output.\\n";

    /* Start for MATLABSystem: '<Root>/GPIO Read' */
    motor_movement_DW.obj_b.matlabCodegenIsDeleted = false;
    motor_movement_DW.obj_b.isInitialized = 1;
    EXT_GPIO_init(23U, false);
    motor_movement_DW.obj_b.isSetupComplete = true;

    /* Start for MATLABSystem: '<Root>/TCP//IP Receive' */
    motor_movement_SystemCore_setup(&motor_movement_DW.obj_n);

    /* Start for MATLABSystem: '<Root>/Direction Pin' */
    motor_movement_DW.obj_h.matlabCodegenIsDeleted = false;
    motor_movement_DW.obj_h.isInitialized = 1;
    EXT_GPIO_init(18U, true);
    motor_movement_DW.obj_h.isSetupComplete = true;

    /* Start for MATLABSystem: '<Root>/Enable Pin' */
    motor_movement_DW.obj_j.matlabCodegenIsDeleted = false;
    motor_movement_DW.obj_j.isInitialized = 1;
    EXT_GPIO_init(17U, true);
    motor_movement_DW.obj_j.isSetupComplete = true;

    /* Start for MATLABSystem: '<Root>/Step Pin' */
    motor_movement_DW.obj.matlabCodegenIsDeleted = false;
    motor_movement_DW.obj.isInitialized = 1;
    motor_movement_DW.obj.PinNumber = 15U;
    ret = EXT_PWMBlock_init(15U, 1000U, 0.0);
    if (ret != 0) {
      for (ret = 0; ret < 45; ret++) {
        b[ret] = b_0[ret];
      }

      printf(&b[0], 15U);
    }

    motor_movement_DW.obj.isSetupComplete = true;

    /* End of Start for MATLABSystem: '<Root>/Step Pin' */
  }
}

/* Model terminate function */
void motor_movement_terminate(void)
{
  /* Terminate for MATLABSystem: '<Root>/GPIO Read' */
  if (!motor_movement_DW.obj_b.matlabCodegenIsDeleted) {
    motor_movement_DW.obj_b.matlabCodegenIsDeleted = true;
    if ((motor_movement_DW.obj_b.isInitialized == 1) &&
        motor_movement_DW.obj_b.isSetupComplete) {
      EXT_GPIO_terminate(23U);
    }
  }

  /* End of Terminate for MATLABSystem: '<Root>/GPIO Read' */

  /* Terminate for MATLABSystem: '<Root>/Direction Pin' */
  if (!motor_movement_DW.obj_h.matlabCodegenIsDeleted) {
    motor_movement_DW.obj_h.matlabCodegenIsDeleted = true;
    if ((motor_movement_DW.obj_h.isInitialized == 1) &&
        motor_movement_DW.obj_h.isSetupComplete) {
      EXT_GPIO_terminate(18U);
    }
  }

  /* End of Terminate for MATLABSystem: '<Root>/Direction Pin' */

  /* Terminate for MATLABSystem: '<Root>/Enable Pin' */
  if (!motor_movement_DW.obj_j.matlabCodegenIsDeleted) {
    motor_movement_DW.obj_j.matlabCodegenIsDeleted = true;
    if ((motor_movement_DW.obj_j.isInitialized == 1) &&
        motor_movement_DW.obj_j.isSetupComplete) {
      EXT_GPIO_terminate(17U);
    }
  }

  /* End of Terminate for MATLABSystem: '<Root>/Enable Pin' */
  /* Terminate for MATLABSystem: '<Root>/Step Pin' */
  if (!motor_movement_DW.obj.matlabCodegenIsDeleted) {
    motor_movement_DW.obj.matlabCodegenIsDeleted = true;
    if ((motor_movement_DW.obj.isInitialized == 1) &&
        motor_movement_DW.obj.isSetupComplete) {
      EXT_PWMBlock_terminate(motor_movement_DW.obj.PinNumber);
    }
  }

  /* End of Terminate for MATLABSystem: '<Root>/Step Pin' */
}

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
