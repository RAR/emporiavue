typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef signed short int16_t;
typedef unsigned short uint16_t;
typedef signed int int32_t;
typedef unsigned int uint32_t;
typedef signed long long int64_t;
typedef unsigned long long uint64_t;

typedef uint8_t bool;
#define false 0
#define true 1
#define CHAR_BIT 8
#define UINT32_C(value) value##UL
#define INT16_MIN (-32768)
#define INT16_MAX 32767

__attribute__((used, noinline, optimize("O0")))
void *memset(void *dst, int value, unsigned int length)
{
	volatile uint8_t *out = (volatile uint8_t *) dst;
	while (length-- > 0)
		*out++ = (uint8_t) value;
	return dst;
}

__attribute__((used, noinline, optimize("O0")))
void *memcpy(void *dst, const void *src, unsigned int length)
{
	volatile uint8_t *out = (volatile uint8_t *) dst;
	const volatile uint8_t *in = (const volatile uint8_t *) src;
	while (length-- > 0)
		*out++ = *in++;
	return dst;
}

typedef volatile       uint8_t  RwReg8;  /**< Read-Write  8-bit register (volatile unsigned int) */
typedef volatile       uint8_t  RoReg8;  /**< Read only  8-bit register (volatile const unsigned int) */
typedef volatile       uint16_t RwReg16; /**< Read-Write 16-bit register (volatile unsigned int) */
typedef volatile       uint16_t RoReg16; /**< Read only 16-bit register (volatile unsigned int) */
typedef volatile       uint32_t RwReg;   /**< Read-Write 32-bit register (volatile unsigned int) */
typedef volatile       uint32_t RoReg;   /**< Read only 32-bit register (volatile const unsigned int) */

#ifdef __cplusplus
  #define   __I     volatile             /*!< Defines 'read only' permissions                 */
#else
  #define   __I     volatile const       /*!< Defines 'read only' permissions                 */
#endif
#define     __O     volatile             /*!< Defines 'write only' permissions                */
#define     __IO    volatile             /*!< Defines 'read / write' permissions              */

#define REG_ADC_CTRLA              (*(RwReg8 *)0x42002000UL)
#define REG_ADC_REFCTRL            (*(RwReg8 *)0x42002001UL)
#define REG_ADC_SAMPCTRL           (*(RwReg8 *)0x42002003UL)
#define REG_ADC_CTRLB              (*(RwReg16*)0x42002004UL)
#define REG_ADC_INPUTCTRL          (*(RwReg  *)0x42002010UL)
#define REG_ADC_EVCTRL             (*(RwReg8 *)0x42002014UL) /**< \brief (ADC) Event Control */
#define REG_ADC_INTFLAG            (*(RwReg8 *)0x42002018UL) /**< \brief (ADC) Interrupt Flag Status and Clear */
#define REG_ADC_STATUS             (*(RoReg8 *)0x42002019UL) /**< \brief (ADC) Status */
#define REG_ADC_RESULT             (*(RoReg16*)0x4200201AUL) /**< \brief (ADC) Result */
#define REG_ADC_CALIB              (*(RwReg16*)0x42002028UL)

#define REG_SYSCTRL_PCLKSR         (*(RoReg  *)0x4000080CUL) /**< \brief (SYSCTRL) Power and Clocks Status */
#define REG_SYSCTRL_OSC32K         (*(RwReg  *)0x40000818UL) /**< \brief (SYSCTRL) 32kHz Internal Oscillator (OSC32K) Control */
#define REG_SYSCTRL_OSC8M          (*(RwReg  *)0x40000820UL) /**< \brief (SYSCTRL) 8MHz Internal Oscillator (OSC8M) Control */
#define REG_SYSCTRL_DFLLCTRL       (*(RwReg16*)0x40000824UL) /**< \brief (SYSCTRL) DFLL48M Control */
#define REG_SYSCTRL_DFLLVAL        (*(RwReg  *)0x40000828UL) /**< \brief (SYSCTRL) DFLL48M Value */

#define REG_GCLK_STATUS            (*(RoReg8 *)0x40000C01UL) /**< \brief (GCLK) Status */
#define REG_GCLK_CLKCTRL           (*(RwReg16*)0x40000C02UL) /**< \brief (GCLK) Generic Clock Control */
#define REG_GCLK_GENCTRL           (*(RwReg  *)0x40000C04UL) /**< \brief (GCLK) Generic Clock Generator Control */
#define REG_GCLK_GENDIV            (*(RwReg  *)0x40000C08UL) /**< \brief (GCLK) Generic Clock Generator Division */

#define REG_PM_SLEEP               (*(RwReg8 *)0x40000401UL) /**< \brief (PM) Sleep Mode */
#define REG_PM_APBCMASK            (*(RwReg  *)0x40000420UL) /**< \brief (PM) APBC Mask */

#define REG_NVMCTRL_CTRLB          (*(RwReg  *)0x41004004UL) /**< \brief (NVMCTRL) Control B */

#define REG_EVSYS_CHANNEL          (*(RwReg  *)0x42000404UL) /**< \brief (EVSYS) Channel */
#define REG_EVSYS_USER             (*(RwReg16*)0x42000408UL) /**< \brief (EVSYS) User Multiplexer */

#define REG_TC1_CTRLA              (*(RwReg16*)0x42001800UL) /**< \brief (TC1) Control A */
#define REG_TC1_EVCTRL             (*(RwReg16*)0x4200180AUL) /**< \brief (TC1) Event Control */
#define REG_TC1_INTFLAG            (*(RwReg8 *)0x4200180EUL) /**< \brief (TC1) Interrupt Flag Status and Clear */
#define REG_TC1_STATUS             (*(RoReg8 *)0x4200180FUL) /**< \brief (TC1) Status */
#define REG_TC1_COUNT16_CC0        (*(RwReg16*)0x42001818UL) /**< \brief (TC1) COUNT16 Compare/Capture 0 */

#define REG_PORT_DIR	            (*(RwReg  *)0x41004400UL)
#define REG_PORT_DIRSET             (*(RwReg  *)0x41004408UL)
#define REG_PORT_OUT	            (*(RwReg  *)0x41004410UL)
#define REG_PORT_OUTCLR            (*(RwReg  *)0x41004414UL) /**< \brief (PORT) Data Output Value Clear 0 */
#define REG_PORT_OUTSET            (*(RwReg  *)0x41004418UL) /**< \brief (PORT) Data Output Value Set 0 */
#define REG_PORT_IN                (*(RoReg  *)0x41004420UL)
#define REG_PINCFG2	            (*(RwReg8 *)0x41004442UL)
#define REG_PINCFG3	            (*(RwReg8 *)0x41004443UL)
#define REG_PINCFG4	            (*(RwReg8 *)0x41004444UL)
#define REG_PINCFG5	            (*(RwReg8 *)0x41004445UL)
#define REG_PINCFG6	            (*(RwReg8 *)0x41004446UL)
#define REG_PINCFG7	            (*(RwReg8 *)0x41004447UL)
#define REG_PINCFG8	            (*(RwReg8 *)0x41004448UL)
#define REG_PINCFG9	            (*(RwReg8 *)0x41004449UL)
#define REG_PINCFG10	            (*(RwReg8 *)0x4100444AUL)
#define REG_PINCFG11	            (*(RwReg8 *)0x4100444BUL)
#define REG_PINCFG14	            (*(RwReg8 *)0x4100444EUL)
#define REG_PINCFG15	            (*(RwReg8 *)0x4100444FUL)
#define REG_PINCFG22	            (*(RwReg8 *)0x41004456UL)
#define REG_PINCFG23	            (*(RwReg8 *)0x41004457UL)
#define REG_PINCFG25	            (*(RwReg8 *)0x41004459UL)
#define REG_PINCFG27	            (*(RwReg8 *)0x4100445BUL)
#define REG_PINCFG28	            (*(RwReg8 *)0x4100445CUL)
#define REG_PINCFG30	            (*(RwReg8 *)0x4100445EUL)
#define REG_PINCFG31	            (*(RwReg8 *)0x4100445FUL)
#define REG_PORT_PMUX1             (*(RwReg8 *)0x41004431UL)
#define REG_PORT_PMUX2	            (*(RwReg8 *)0x41004432UL)
#define REG_PORT_PMUX3	            (*(RwReg8 *)0x41004433UL)
#define REG_PORT_PMUX5	            (*(RwReg8 *)0x41004435UL)
#define REG_PORT_PMUX7	            (*(RwReg8 *)0x41004437UL)
#define REG_PORT_PMUX11            (*(RwReg8 *)0x4100443BUL)

#define REG_DMAC_CTRL              (*(RwReg16*)0x41004800UL) /**< \brief (DMAC) Control */
#define REG_DMAC_CRCCTRL           (*(RwReg16*)0x41004802UL) /**< \brief (DMAC) CRC Control */
#define REG_DMAC_CRCDATAIN         (*(RwReg  *)0x41004804UL) /**< \brief (DMAC) CRC Data Input */
#define REG_DMAC_CRCCHKSUM         (*(RwReg  *)0x41004808UL) /**< \brief (DMAC) CRC Checksum */
#define REG_DMAC_CRCSTATUS         (*(RwReg8 *)0x4100480CUL) /**< \brief (DMAC) CRC Status */
#define REG_DMAC_PRICTRL0          (*(RwReg  *)0x41004814UL) /**< \brief (DMAC) Priority Control 0 */
#define REG_DMAC_INTSTATUS         (*(RoReg  *)0x41004824UL) /**< \brief (DMAC) Interrupt Status */
#define REG_DMAC_BUSYCH            (*(RoReg  *)0x41004828UL) /**< \brief (DMAC) Busy Channels */
#define REG_DMAC_PENDCH            (*(RoReg  *)0x4100482CUL) /**< \brief (DMAC) Pending Channels */
#define REG_DMAC_BASEADDR          (*(RwReg  *)0x41004834UL) /**< \brief (DMAC) Descriptor Memory Section Base Address */
#define REG_DMAC_WRBADDR           (*(RwReg  *)0x41004838UL) /**< \brief (DMAC) Write-Back Memory Section Base Address */
#define REG_DMAC_CHID              (*(RwReg8 *)0x4100483FUL) /**< \brief (DMAC) Channel ID */
#define REG_DMAC_CHCTRLA           (*(RwReg8 *)0x41004840UL) /**< \brief (DMAC) Channel Control A */
#define REG_DMAC_CHCTRLB           (*(RwReg  *)0x41004844UL) /**< \brief (DMAC) Channel Control B */
#define REG_DMAC_CHINTENSET        (*(RwReg8 *)0x4100484DUL) /**< \brief (DMAC) Channel Interrupt Enable Set */
#define REG_DMAC_CHINTFLAG         (*(RwReg8 *)0x4100484EUL) /**< \brief (DMAC) Channel Interrupt Flag Status and Clear */

#define REG_NVIC_SETENA	    (*(RwReg  *)0xE000E100UL) //Interrupt Set-Enable Register
#define REG_NVIC_PRIO1		    (*(RwReg  *)0xE000E404UL) //Interrupt Priority Register 1
#define REG_NVIC_PRIO2		    (*(RwReg  *)0xE000E408UL) //Interrupt Priority Register 1
#define REG_NVIC_PRIO3		    (*(RwReg  *)0xE000E40CUL) //Interrupt Priority Register 3
#define REG_SCB_SCR                (*(RwReg  *)0xE000ED10UL) //System Control Register

#define SCB_SCR_SLEEPDEEP_MASK     (1UL << 2)

#define REG_SERCOM1_CTRLA          (*(RwReg  *)0x42000C00UL)
#define REG_SERCOM1_CTRLB          (*(RwReg  *)0x42000C04UL)
#define REG_SERCOM1_BAUD           (*(RwReg8 *)0x42000C0CUL)
#define REG_SERCOM1_INTENCLR       (*(RwReg8 *)0x42000C14UL)
#define REG_SERCOM1_INTENSET       (*(RwReg8 *)0x42000C16UL)
#define REG_SERCOM1_INTFLAG        (*(RwReg8 *)0x42000C18UL)
#define REG_SERCOM1_SYNCBUSY       (*(RoReg  *)0x42000C1CUL)
#define REG_SERCOM1_DATA           (*(RwReg8 *)0x42000C28UL)

#ifdef EMPORIAVUE_TARGET_VUE3
#define REG_SERCOM0_CTRLA          (*(RwReg  *)0x42000800UL)
#define REG_SERCOM0_CTRLB          (*(RwReg  *)0x42000804UL)
#define REG_SERCOM0_BAUD           (*(RwReg16*)0x4200080CUL)
#define REG_SERCOM0_INTENSET       (*(RwReg8 *)0x42000816UL)
#define REG_SERCOM0_INTFLAG        (*(RwReg8 *)0x42000818UL)
#define REG_SERCOM0_STATUS         (*(RwReg16*)0x4200081AUL)
#define REG_SERCOM0_SYNCBUSY       (*(RoReg  *)0x4200081CUL)
#define REG_SERCOM0_DATA           (*(RoReg16*)0x42000828UL)
#endif

#define STATUS_SYNCBUSY_BIT        0x80

#define SCB_VTOR_TBLOFF_Pos                 7                                             /*!< SCB VTOR: TBLOFF Position */
#define SCB_VTOR_TBLOFF_Msk                (0x1FFFFFFUL << SCB_VTOR_TBLOFF_Pos)           /*!< SCB VTOR: TBLOFF Mask */

#define DUMMY __attribute__ ((weak, alias ("irq_handler_dummy")))

#define BOOT_DIAG_MAGIC 0x45565344UL
#define BOOT_STAGE_RESET_ENTRY 1
#define BOOT_STAGE_MAIN_ENTRY 10
#define BOOT_STAGE_NVM_READ_WAIT 11
#define BOOT_STAGE_PORT_CONFIGURED 16
#define BOOT_STAGE_CLOCK_CONFIGURED 17
#define BOOT_STAGE_NVM_MANUAL_WRITE 18
#define BOOT_STAGE_EVENT_SYSTEM_CONFIGURED 19
#define BOOT_STAGE_DMAC_CONFIGURED 20
#define BOOT_STAGE_ADC_CONFIGURED 21
#define BOOT_STAGE_TC1_CONFIGURED 22
#define BOOT_STAGE_NVIC_CONFIGURED 23
#define BOOT_STAGE_DMA_ENABLED 24
#define BOOT_STAGE_ADC_ENABLED 25
#define BOOT_STAGE_TC1_ENABLED 26
#define BOOT_STAGE_SERCOM1_CONFIGURED 27
#define BOOT_STAGE_MAIN_LOOP 28
#define BOOT_STAGE_SERCOM0_CONFIGURED 29
#define BOOT_STAGE_HARDFAULT 0xff

struct BootDiagnosticType
{
	uint32_t magic;
	uint32_t stage;
	uint32_t hardfault_lr;
	uint32_t hardfault_msp;
	uint32_t hardfault_psp;
	uint32_t stacked_pc;
	uint32_t stacked_lr;
	uint32_t reserved;
};

__attribute__((used, section(".bss.$RESERVED")))
volatile struct BootDiagnosticType BootDiagnostic;

static inline void set_boot_stage(uint32_t stage)
{
	BootDiagnostic.magic = BOOT_DIAG_MAGIC;
	BootDiagnostic.stage = stage;
}

volatile bool dmabool = false;
volatile bool DiscardNextAdcScan = false;
volatile uint8_t DMAresultIndex = 0;
uint8_t MuxCounter = 0; //Varies between 0 and 7 to switch between the 8 muxes, each serving 2 50A CT's
#ifdef EMPORIAVUE_TARGET_VUE3
#define ADC_CHANNEL_COUNT 5
// Vue 3 scans AIN3..AIN7: three main-current inputs followed by two multiplexed branch-current inputs.
#else
#define ADC_CHANNEL_COUNT 8
// Vue 2 layout: MainCT1_V, MainCT1_A, MainCT2_V, MainCT2_A, MainCT3_V, MainCT3_A, Mux1_A, Mux2_A.
#endif
#define ADC_SCAN_BUFFER_COUNT 2
// One completed scan is copied while DMA fills the other. SPI delay alignment
// is performed on the ESP32; no older ADC scan is consumed on the SAMD09.
int16_t DMAresults[ADC_SCAN_BUFFER_COUNT][ADC_CHANNEL_COUNT];

#ifdef EMPORIAVUE_TARGET_VUE3
const uint32_t outputpinTable [8] = { 0, 0x10000, 0x20000, 0x30000, 0x1000000, 0x1010000, 0x1020000, 0x1030000 };
#define MUX_SWITCH_GUARD_PIN_MASK 0x100UL // Vue 3 stock firmware changes the PA08 pull while switching.
#else
const uint32_t outputpinTable [8] = { 0x1000000, 0x1010000, 0x1020000, 0x1030000, 0, 0x10000, 0x20000, 0x30000 }; //all possible combinations of pin 16, 17 and 24.
#define MUX_SWITCH_GUARD_PIN_MASK 0x2000000UL // PA25
#endif

#ifndef EMPORIAVUE_HARDWARE_ID
#define EMPORIAVUE_HARDWARE_ID       2
#endif
#ifndef EMPORIAVUE_MODE_ID
#define EMPORIAVUE_MODE_ID           2
#endif
#ifndef EMPORIAVUE_FIRMWARE_VERSION
#define EMPORIAVUE_FIRMWARE_VERSION  11
#endif

#ifdef EMPORIAVUE_TARGET_VUE3
#define TC1_ADC_TRIGGER_PERIOD         0x9F
#define ADC_INPUTCTRL_SCAN_DIFF_GAIN2  0x1340000UL
#define SPI_FRAME_VERSION              2
#define SPI_FRAME_TYPE_RAW_SAMPLES     2
#define SPI_SAMPLE_PERIOD_TICKS        816
#else
#define TC1_ADC_TRIGGER_PERIOD         0x4C
#define ADC_INPUTCTRL_SCAN_DIFF_GAIN2  0x1270000UL
#define SPI_FRAME_VERSION              1
#define SPI_FRAME_TYPE_RAW_SAMPLES     1
#define SPI_SAMPLE_PERIOD_TICKS        632
#endif
#define ADC_SAMPLE_TIME_LENGTH         1
#define ADC_REFCTRL_VREFA              3
#define ADC_CTRLB_DIV8_12BIT_DIFF      0x101

#define SPI_FRAME_SIZE                 1024
#define SPI_HEADER_SIZE                12
#define SPI_CRC_SIZE                   4
#define SPI_PAYLOAD_SIZE               (SPI_FRAME_SIZE - SPI_HEADER_SIZE - SPI_CRC_SIZE)
#define SPI_RAW_SCAN_COUNT             56
#define SPI_FLAG_OVERRUN               0x0001
#define SPI_FLAG_DMA_ERROR             0x0002
#define SPI_FLAG_VOLTAGE_ERROR         0x0004
#define SPI_FLAG_ADC_OVERRUN           0x8000
#define SPI_FRAME_CS_PIN_MASK          0x80000000UL  // PA31/SWDIO, active-low SPI frame/CS.

#define DMA_CHANNEL_ADC                0
#define DMA_CHANNEL_SPI_TX             1
#define DMA_CHANNEL_COUNT              2
#define DMA_CHANNEL_MASK               ((1UL << DMA_CHANNEL_COUNT) - 1UL)
#define DMA_TRIGGER_ADC_RESRDY         0x12
#define DMA_TRIGGER_SERCOM1_TX         0x04
#define DMA_CHCTRLB_TRIGACT_BEAT       0x800000UL
#define DMA_CHCTRLB_PRIORITY(level)    (((uint32_t) (level) & 0x3UL) << 5)
// On the SAMD09 a lower level number has higher arbitration priority.
#define DMA_CHCTRLB_PRIORITY_CRITICAL   DMA_CHCTRLB_PRIORITY(0)
#define DMA_CHCTRLB_PRIORITY_BACKGROUND DMA_CHCTRLB_PRIORITY(3)
#define DMA_INT_TRANSFER_ERROR         0x01
#define DMA_INT_TRANSFER_COMPLETE      0x02
#define DMA_INT_SUSPEND                0x04
#define DMA_CHANNEL_ENABLE             0x02
#define ADC_INTFLAG_OVERRUN            0x02
#define SERCOM_INT_TXC                  0x02
#define SERCOM_INT_RXC                  0x04
#define SERCOM_INT_ERROR                0x80
#define USART_STATUS_RX_ERRORS          0x0007 // PERR, FERR, BUFOVF (write-one-to-clear).

struct __attribute__((__packed__)) SpiFrameHeader
{
	uint8_t version;
	uint8_t type;
	uint16_t length;
	uint16_t sequence;
	uint16_t flags;
	uint32_t sample_counter;
};

struct __attribute__((__packed__)) SpiRawScan
{
	int16_t value[8];
	uint8_t mux_index;
	uint8_t reserved;
};

struct __attribute__((__packed__, aligned(4))) SpiRawFrame
{
	struct SpiFrameHeader header;
	struct SpiRawScan scans[SPI_RAW_SCAN_COUNT];
	uint32_t crc32;
};

typedef char SpiRawFrameSizeCheck[(sizeof(struct SpiRawFrame) == SPI_FRAME_SIZE) ? 1 : -1];
typedef char SpiRawPayloadSizeCheck[(sizeof(struct SpiRawScan) * SPI_RAW_SCAN_COUNT == SPI_PAYLOAD_SIZE) ? 1 : -1];

#define SPI_FRAME_BUFFER_COUNT         3
#define SPI_READY_QUEUE_CAPACITY       (SPI_FRAME_BUFFER_COUNT - 1)

// Keep equal-alignment globals together to avoid unnecessary RAM padding.
volatile uint32_t SpiSampleCounter = 0;
volatile uint16_t SpiFrameSequence = 0;
volatile uint16_t SpiPendingFlags = 0;
struct SpiRawFrame SpiFrames[SPI_FRAME_BUFFER_COUNT];
volatile uint8_t SpiBuildFrameIndex = 0;
volatile uint8_t SpiReadyHead = 0;
volatile uint8_t SpiReadyCount = 0;
volatile uint8_t SpiBuildScanIndex = 0;
volatile bool SpiTxActive = false;
volatile bool SpiTxAwaitingComplete = false;
volatile uint8_t SpiReadyFrameIndex[SPI_READY_QUEUE_CAPACITY] __attribute__((aligned(1)));

#ifdef EMPORIAVUE_TARGET_VUE3
volatile uint32_t VoltagePacketGeneration = 0;
volatile uint32_t VoltageUartErrors = 0;
uint32_t VoltagePacketConsumedGeneration = 0;
uint32_t VoltageTelegramUpdates = 0;
uint32_t VoltageRejectedTelegrams = 0;
uint32_t VoltageAgeScans = 0;
// These small CPU-only arrays need only their element alignment, not the
// compiler's preferred word alignment. DMA descriptors/frames stay unchanged.
int16_t DecodedVoltage[3] __attribute__((aligned(2)));
volatile uint8_t VoltagePacketBuild[6] __attribute__((aligned(1)));
volatile uint8_t VoltagePacketPublished[6] __attribute__((aligned(1)));
volatile uint8_t VoltagePacketBuildLength = 0;
// Once acquired, keep the last validated voltage snapshot until a newer valid
// UART telegram replaces it.
bool VoltageValuesValid = false;
#endif

static uint32_t spi_enter_critical(void)
{
	uint32_t primask;
	__asm__ __volatile__(
		"mrs %0, primask\n"
		"cpsid i"
		: "=r" (primask)
		:
		: "memory");
	return primask;
}

static void spi_exit_critical(uint32_t primask)
{
	__asm__ __volatile__("msr primask, %0" : : "r" (primask) : "memory");
}

static void configure_idle_sleep(void)
{
	// IDLE0 stops only the CPU clock. Timer, ADC, DMA and SERCOM clocks keep
	// running, so raw-sample acquisition remains entirely hardware-timed.
	REG_PM_SLEEP = 0;
	REG_SCB_SCR &= ~SCB_SCR_SLEEPDEEP_MASK;
	__asm__ __volatile__("dsb sy" ::: "memory");
	__asm__ __volatile__("isb sy" ::: "memory");
}

static void wait_for_spi_work(void)
{
	// No WFI on Vue 3 (emporiavue#9). Waking from WFI with the DMAC busy, the CPU
	// fetched wrong instruction words: a stale Flash word (msr after wfi decoded as a BL
	// into unmapped memory), and even from SRAM the SPI DMA descriptor's first word.
	// Both hard-faulted. The board is mains powered, so the main loop simply polls.
}

static uint8_t spi_ready_queue_contains(uint8_t frame_index)
{
	for (uint8_t offset = 0; offset < SpiReadyCount; offset++)
	{
		const uint8_t queue_index = (uint8_t) ((SpiReadyHead + offset) % SPI_READY_QUEUE_CAPACITY);
		if (SpiReadyFrameIndex[queue_index] == frame_index)
			return 1;
	}
	return 0;
}

static uint8_t spi_find_free_build_frame(void)
{
	for (uint8_t frame_index = 0; frame_index < SPI_FRAME_BUFFER_COUNT; frame_index++)
	{
		if (!spi_ready_queue_contains(frame_index))
			return frame_index;
	}
	return SpiBuildFrameIndex;
}

// IEEE CRC-32 (reflected 0xEDB88320, as the DMAC CRC engine computes it), one lookup per byte.
static const uint32_t Crc32Table[256] = {
	0x00000000UL, 0x77073096UL, 0xEE0E612CUL, 0x990951BAUL, 0x076DC419UL, 0x706AF48FUL,
	0xE963A535UL, 0x9E6495A3UL, 0x0EDB8832UL, 0x79DCB8A4UL, 0xE0D5E91EUL, 0x97D2D988UL,
	0x09B64C2BUL, 0x7EB17CBDUL, 0xE7B82D07UL, 0x90BF1D91UL, 0x1DB71064UL, 0x6AB020F2UL,
	0xF3B97148UL, 0x84BE41DEUL, 0x1ADAD47DUL, 0x6DDDE4EBUL, 0xF4D4B551UL, 0x83D385C7UL,
	0x136C9856UL, 0x646BA8C0UL, 0xFD62F97AUL, 0x8A65C9ECUL, 0x14015C4FUL, 0x63066CD9UL,
	0xFA0F3D63UL, 0x8D080DF5UL, 0x3B6E20C8UL, 0x4C69105EUL, 0xD56041E4UL, 0xA2677172UL,
	0x3C03E4D1UL, 0x4B04D447UL, 0xD20D85FDUL, 0xA50AB56BUL, 0x35B5A8FAUL, 0x42B2986CUL,
	0xDBBBC9D6UL, 0xACBCF940UL, 0x32D86CE3UL, 0x45DF5C75UL, 0xDCD60DCFUL, 0xABD13D59UL,
	0x26D930ACUL, 0x51DE003AUL, 0xC8D75180UL, 0xBFD06116UL, 0x21B4F4B5UL, 0x56B3C423UL,
	0xCFBA9599UL, 0xB8BDA50FUL, 0x2802B89EUL, 0x5F058808UL, 0xC60CD9B2UL, 0xB10BE924UL,
	0x2F6F7C87UL, 0x58684C11UL, 0xC1611DABUL, 0xB6662D3DUL, 0x76DC4190UL, 0x01DB7106UL,
	0x98D220BCUL, 0xEFD5102AUL, 0x71B18589UL, 0x06B6B51FUL, 0x9FBFE4A5UL, 0xE8B8D433UL,
	0x7807C9A2UL, 0x0F00F934UL, 0x9609A88EUL, 0xE10E9818UL, 0x7F6A0DBBUL, 0x086D3D2DUL,
	0x91646C97UL, 0xE6635C01UL, 0x6B6B51F4UL, 0x1C6C6162UL, 0x856530D8UL, 0xF262004EUL,
	0x6C0695EDUL, 0x1B01A57BUL, 0x8208F4C1UL, 0xF50FC457UL, 0x65B0D9C6UL, 0x12B7E950UL,
	0x8BBEB8EAUL, 0xFCB9887CUL, 0x62DD1DDFUL, 0x15DA2D49UL, 0x8CD37CF3UL, 0xFBD44C65UL,
	0x4DB26158UL, 0x3AB551CEUL, 0xA3BC0074UL, 0xD4BB30E2UL, 0x4ADFA541UL, 0x3DD895D7UL,
	0xA4D1C46DUL, 0xD3D6F4FBUL, 0x4369E96AUL, 0x346ED9FCUL, 0xAD678846UL, 0xDA60B8D0UL,
	0x44042D73UL, 0x33031DE5UL, 0xAA0A4C5FUL, 0xDD0D7CC9UL, 0x5005713CUL, 0x270241AAUL,
	0xBE0B1010UL, 0xC90C2086UL, 0x5768B525UL, 0x206F85B3UL, 0xB966D409UL, 0xCE61E49FUL,
	0x5EDEF90EUL, 0x29D9C998UL, 0xB0D09822UL, 0xC7D7A8B4UL, 0x59B33D17UL, 0x2EB40D81UL,
	0xB7BD5C3BUL, 0xC0BA6CADUL, 0xEDB88320UL, 0x9ABFB3B6UL, 0x03B6E20CUL, 0x74B1D29AUL,
	0xEAD54739UL, 0x9DD277AFUL, 0x04DB2615UL, 0x73DC1683UL, 0xE3630B12UL, 0x94643B84UL,
	0x0D6D6A3EUL, 0x7A6A5AA8UL, 0xE40ECF0BUL, 0x9309FF9DUL, 0x0A00AE27UL, 0x7D079EB1UL,
	0xF00F9344UL, 0x8708A3D2UL, 0x1E01F268UL, 0x6906C2FEUL, 0xF762575DUL, 0x806567CBUL,
	0x196C3671UL, 0x6E6B06E7UL, 0xFED41B76UL, 0x89D32BE0UL, 0x10DA7A5AUL, 0x67DD4ACCUL,
	0xF9B9DF6FUL, 0x8EBEEFF9UL, 0x17B7BE43UL, 0x60B08ED5UL, 0xD6D6A3E8UL, 0xA1D1937EUL,
	0x38D8C2C4UL, 0x4FDFF252UL, 0xD1BB67F1UL, 0xA6BC5767UL, 0x3FB506DDUL, 0x48B2364BUL,
	0xD80D2BDAUL, 0xAF0A1B4CUL, 0x36034AF6UL, 0x41047A60UL, 0xDF60EFC3UL, 0xA867DF55UL,
	0x316E8EEFUL, 0x4669BE79UL, 0xCB61B38CUL, 0xBC66831AUL, 0x256FD2A0UL, 0x5268E236UL,
	0xCC0C7795UL, 0xBB0B4703UL, 0x220216B9UL, 0x5505262FUL, 0xC5BA3BBEUL, 0xB2BD0B28UL,
	0x2BB45A92UL, 0x5CB36A04UL, 0xC2D7FFA7UL, 0xB5D0CF31UL, 0x2CD99E8BUL, 0x5BDEAE1DUL,
	0x9B64C2B0UL, 0xEC63F226UL, 0x756AA39CUL, 0x026D930AUL, 0x9C0906A9UL, 0xEB0E363FUL,
	0x72076785UL, 0x05005713UL, 0x95BF4A82UL, 0xE2B87A14UL, 0x7BB12BAEUL, 0x0CB61B38UL,
	0x92D28E9BUL, 0xE5D5BE0DUL, 0x7CDCEFB7UL, 0x0BDBDF21UL, 0x86D3D2D4UL, 0xF1D4E242UL,
	0x68DDB3F8UL, 0x1FDA836EUL, 0x81BE16CDUL, 0xF6B9265BUL, 0x6FB077E1UL, 0x18B74777UL,
	0x88085AE6UL, 0xFF0F6A70UL, 0x66063BCAUL, 0x11010B5CUL, 0x8F659EFFUL, 0xF862AE69UL,
	0x616BFFD3UL, 0x166CCF45UL, 0xA00AE278UL, 0xD70DD2EEUL, 0x4E048354UL, 0x3903B3C2UL,
	0xA7672661UL, 0xD06016F7UL, 0x4969474DUL, 0x3E6E77DBUL, 0xAED16A4AUL, 0xD9D65ADCUL,
	0x40DF0B66UL, 0x37D83BF0UL, 0xA9BCAE53UL, 0xDEBB9EC5UL, 0x47B2CF7FUL, 0x30B5FFE9UL,
	0xBDBDF21CUL, 0xCABAC28AUL, 0x53B39330UL, 0x24B4A3A6UL, 0xBAD03605UL, 0xCDD70693UL,
	0x54DE5729UL, 0x23D967BFUL, 0xB3667A2EUL, 0xC4614AB8UL, 0x5D681B02UL, 0x2A6F2B94UL,
	0xB40BBE37UL, 0xC30C8EA1UL, 0x5A05DF1BUL, 0x2D02EF8DUL
};

#ifdef EMPORIAVUE_TARGET_VUE3
static void write_vue3_voltage_diagnostics(struct SpiRawFrame* frame)
{
	// Optional protocol-v2 extension in previously zero reserved scan bytes.
	// Decode only with the EVUD marker and format version 1. Old receivers ignore
	// these bytes; frame length, header version and CRC coverage are unchanged.
	const uint32_t counters[4] = {
		VoltageTelegramUpdates, VoltageUartErrors, VoltageRejectedTelegrams, VoltageAgeScans
	};
	for (uint8_t counter = 0; counter < 4; counter++)
	{
		const uint32_t value = counters[counter];
		for (uint8_t byte = 0; byte < 4; byte++)
			frame->scans[counter * 4 + byte].reserved = (uint8_t) (value >> (byte * 8));
	}
	frame->scans[16].reserved = 'E';
	frame->scans[17].reserved = 'V';
	frame->scans[18].reserved = 'U';
	frame->scans[19].reserved = 'D';
	frame->scans[20].reserved = 1;
}
#endif

static void finalize_spi_frame(void)
{
	struct SpiRawFrame* frame = &SpiFrames[SpiBuildFrameIndex];

	frame->header.version = SPI_FRAME_VERSION;
	frame->header.type = SPI_FRAME_TYPE_RAW_SAMPLES;
	frame->header.length = SPI_PAYLOAD_SIZE;
	frame->header.sequence = SpiFrameSequence++;
#ifdef EMPORIAVUE_TARGET_VUE3
	// Protocol v2 carries the measured scan period in flag bits 3..14.
	frame->header.flags = (uint16_t) (SpiPendingFlags | (SPI_SAMPLE_PERIOD_TICKS << 3));
	write_vue3_voltage_diagnostics(frame);
#else
	frame->header.flags = SpiPendingFlags;
#endif
	frame->crc32 = 0;
	if (SpiReadyCount >= SPI_READY_QUEUE_CAPACITY)
	{
		// The dropped frame cannot report its errors. Keep them pending until
		// a later frame is actually queued for transmission.
		SpiPendingFlags |= SPI_FLAG_OVERRUN;
		SpiBuildScanIndex = 0;
		return;
	}

	SpiPendingFlags = 0;
	SpiBuildScanIndex = 0;
	const uint8_t ready_tail = (uint8_t) ((SpiReadyHead + SpiReadyCount) % SPI_READY_QUEUE_CAPACITY);
	SpiReadyFrameIndex[ready_tail] = SpiBuildFrameIndex;
	SpiReadyCount++;
	SpiBuildFrameIndex = spi_find_free_build_frame();
	__asm__ __volatile__("dmb sy");
}

static void capture_spi_scan(uint8_t dma_result_index, uint8_t mux_index)
{
	struct SpiRawFrame* frame = &SpiFrames[SpiBuildFrameIndex];

	if (SpiBuildScanIndex == 0)
		frame->header.sample_counter = SpiSampleCounter;

	struct SpiRawScan* scan = &frame->scans[SpiBuildScanIndex];
#ifdef EMPORIAVUE_TARGET_VUE3
	// Preserve the semantic Vue 2 scan layout so the ESP32 can share the same
	// metering implementation: V1/I1, V2/I2, V3/I3, branch mux A/B.
	scan->value[0] = DecodedVoltage[0];
	scan->value[1] = DMAresults[dma_result_index][0];
	scan->value[2] = DecodedVoltage[1];
	scan->value[3] = DMAresults[dma_result_index][1];
	scan->value[4] = DecodedVoltage[2];
	scan->value[5] = DMAresults[dma_result_index][2];
	scan->value[6] = DMAresults[dma_result_index][3];
	scan->value[7] = DMAresults[dma_result_index][4];
	scan->mux_index = mux_index;
	scan->reserved = 0;
#else
	for (uint8_t index = 0; index < ADC_CHANNEL_COUNT; index++)
		scan->value[index] = DMAresults[dma_result_index][index];
	scan->mux_index = mux_index;
	scan->reserved = 0;
	if (SpiBuildScanIndex == 0)
		scan->reserved = (uint8_t) (SPI_SAMPLE_PERIOD_TICKS & 0xFF);
	else if (SpiBuildScanIndex == 1)
		scan->reserved = (uint8_t) ((SPI_SAMPLE_PERIOD_TICKS >> 8) & 0xFF);
#endif

	SpiSampleCounter++;
	SpiBuildScanIndex++;
	if (SpiBuildScanIndex >= SPI_RAW_SCAN_COUNT)
		finalize_spi_frame();
}

struct DMAdescriptorType {
  uint16_t BTCTRL;
  uint16_t BTCNT;
  uint32_t SRCADDR;
  uint32_t DSTADDR;
  uint32_t DESCADDR;
};

typedef char DMADescriptorSizeCheck[(sizeof(struct DMAdescriptorType) == 16) ? 1 : -1];
volatile struct DMAdescriptorType DMAdescriptor[DMA_CHANNEL_COUNT] __attribute__((aligned(16)));
volatile struct DMAdescriptorType DMAdescriptorwriteback[DMA_CHANNEL_COUNT] __attribute__((aligned(16)));

#define __SIZE_OF__(x) \
({x __tmp_x_[2]; \
((unsigned int)(&__tmp_x_[1]) - (unsigned int)(&__tmp_x_[0])); \
})

extern unsigned int _etext;
extern unsigned int _data;
extern unsigned int _edata;
extern unsigned int _bss;
extern unsigned int _ebss;
extern int main(void);

void irq_handler_reset(void);
void irq_handler_dmac(void);
void irq_handler_sercom1(void);
DUMMY void irq_handler_nmi(void);
void irq_handler_hard_fault(void);
DUMMY void irq_handler_sv_call(void);
DUMMY void irq_handler_pend_sv(void);
DUMMY void irq_handler_sys_tick(void);
DUMMY void irq_handler_pm(void);
DUMMY void irq_handler_sysctrl(void);
DUMMY void irq_handler_wdt(void);
DUMMY void irq_handler_rtc(void);
DUMMY void irq_handler_eic(void);
DUMMY void irq_handler_nvmctrl(void);
DUMMY void irq_handler_evsys(void);
#ifdef EMPORIAVUE_TARGET_VUE3
void irq_handler_sercom0(void);
#else
DUMMY void irq_handler_sercom0(void);
#endif
DUMMY void irq_handler_tc1(void);
DUMMY void irq_handler_tc2(void);
DUMMY void irq_handler_adc(void);
DUMMY void irq_handler_ptc(void);

extern void _stack_top(void);

//-----------------------------------------------------------------------------
__attribute__ ((used, section(".vectors")))
void (* const vectors[])(void) =
{
  &_stack_top,                   // 0 - Initial Stack Pointer Value

  // Cortex-M0+ handlers
  irq_handler_reset,             // 1 - Reset
  irq_handler_nmi,               // 2 - NMI
  irq_handler_hard_fault,        // 3 - Hard Fault
  0,                             // 4 - Reserved
  0,                             // 5 - Reserved
  0,                             // 6 - Reserved
  0,                             // 7 - Reserved
  0,                             // 8 - Reserved
  0,                             // 9 - Reserved
  0,                             // 10 - Reserved
  irq_handler_sv_call,           // 11 - SVCall
  0,                             // 12 - Reserved
  0,                             // 13 - Reserved
  irq_handler_pend_sv,           // 14 - PendSV
  irq_handler_sys_tick,          // 15 - SysTick

  // Peripheral handlers
  irq_handler_pm,                // 0 - Power Manager
  irq_handler_sysctrl,           // 1 - System Controller
  irq_handler_wdt,               // 2 - Watchdog Timer
  irq_handler_rtc,               // 3 - Real Time Counter
  irq_handler_eic,               // 4 - External Interrupt Controller
  irq_handler_nvmctrl,           // 5 - Non-Volatile Memory Controller
  irq_handler_dmac,              // 6 - Direct Memory Access Controller, we use this interrupt!
  0,		                 // 7 - Reserved (usb)
  irq_handler_evsys,             // 8 - Event System
  irq_handler_sercom0,           // 9 - Serial Communication Interface 0
  irq_handler_sercom1,           // 10 - Serial Communication Interface 1, we use this interrupt!
  0,		                  // 11 - Reserved (Serial Communication Interface 2)
  0,                             // 12 - Reserved
  irq_handler_tc1,               // 13 - Timer/Counter 1
  irq_handler_tc2,               // 14 - Timer/Counter 2
  irq_handler_adc,               // 15 - Analog-to-Digital Converter
  0,                             // 16 - Reserved
  0,		                 // 17 - Digital-to-Analog Converter
  irq_handler_ptc,               // 18 - Peripheral Touch Controller
};

/* Memory mapping of Cortex-M0+ Hardware */
#define SCS_BASE            (0xE000E000UL)                            /*!< System Control Space Base Address */
#define SysTick_BASE        (SCS_BASE +  0x0010UL)                    /*!< SysTick Base Address              */
#define NVIC_BASE           (SCS_BASE +  0x0100UL)                    /*!< NVIC Base Address                 */
#define SCB_BASE            (SCS_BASE +  0x0D00UL)                    /*!< System Control Block Base Address */

#define SCB                 ((SCB_Type       *)     SCB_BASE      )   /*!< SCB configuration struct           */
#define SysTick             ((SysTick_Type   *)     SysTick_BASE  )   /*!< SysTick configuration struct       */
#define NVIC                ((NVIC_Type      *)     NVIC_BASE     )   /*!< NVIC configuration struct          */

typedef struct
{
  __I  uint32_t CPUID;                   /*!< Offset: 0x000 (R/ )  CPUID Base Register                                   */
  __IO uint32_t ICSR;                    /*!< Offset: 0x004 (R/W)  Interrupt Control and State Register                  */
  __IO uint32_t VTOR;                    /*!< Offset: 0x008 (R/W)  Vector Table Offset Register                          */
  __IO uint32_t AIRCR;                   /*!< Offset: 0x00C (R/W)  Application Interrupt and Reset Control Register      */
  __IO uint32_t SCR;                     /*!< Offset: 0x010 (R/W)  System Control Register                               */
  __IO uint32_t CCR;                     /*!< Offset: 0x014 (R/W)  Configuration Control Register                        */
       uint32_t RESERVED1;
  __IO uint32_t SHP[2];                  /*!< Offset: 0x01C (R/W)  System Handlers Priority Registers. [0] is RESERVED   */
  __IO uint32_t SHCSR;                   /*!< Offset: 0x024 (R/W)  System Handler Control and State Register             */
} SCB_Type;

void irq_handler_dummy(void)
{
  while (1);
}

__attribute__((naked, used)) void irq_handler_hard_fault(void)
{
	__asm__ __volatile__(
		"ldr r0, =BootDiagnostic\n"
		"ldr r1, =0x45565344\n"
		"str r1, [r0, #0]\n"
		"movs r1, #255\n"
		"str r1, [r0, #4]\n"
		"mov r1, lr\n"
		"str r1, [r0, #8]\n"
		"mrs r2, msp\n"
		"str r2, [r0, #12]\n"
		"mrs r1, psp\n"
		"str r1, [r0, #16]\n"
		"ldr r3, =0x20000000\n"
		"cmp r2, r3\n"
		"blo 1f\n"
		"ldr r3, =0x20001000\n"
		"cmp r2, r3\n"
		"bhs 1f\n"
		"ldr r1, [r2, #24]\n"
		"str r1, [r0, #20]\n"
		"ldr r1, [r2, #20]\n"
		"str r1, [r0, #24]\n"
		"1:\n"
		"b 1b\n"
	);
}

void irq_handler_reset(void)
{
  set_boot_stage(BOOT_STAGE_RESET_ENTRY);

  unsigned int *src, *dst;

  src = &_etext;
  dst = &_data;
  while (dst < &_edata)
    *dst++ = *src++;

  dst = &_bss;
  while (dst < &_ebss)
    *dst++ = 0;

  SCB->VTOR = (uint32_t)vectors;

  main();

  while (1);
}

#ifdef EMPORIAVUE_TARGET_VUE3
void irq_handler_sercom0(void)
{
	// Read STATUS before DATA: USART errors describe the next unread byte.
	// IBON is enabled, so an overflow requires draining the receive FIFO.
	const uint16_t errors = REG_SERCOM0_STATUS & USART_STATUS_RX_ERRORS;
	if (errors != 0 || (REG_SERCOM0_INTFLAG & SERCOM_INT_ERROR) != 0)
	{
		while ((REG_SERCOM0_INTFLAG & SERCOM_INT_RXC) != 0)
			(void) REG_SERCOM0_DATA;
		REG_SERCOM0_STATUS = USART_STATUS_RX_ERRORS;
		REG_SERCOM0_INTFLAG = SERCOM_INT_ERROR;
		VoltagePacketBuildLength = 0;
		// A receive error does not invalidate an earlier complete telegram or
		// the last accepted voltage. Report it independently of sample validity.
		VoltageUartErrors++;
		return;
	}
	if ((REG_SERCOM0_INTFLAG & SERCOM_INT_RXC) == 0)
		return;
	const uint8_t value = (uint8_t) REG_SERCOM0_DATA;

	// Only this ISR owns partial reception. ADC boundaries must never discard
	// a telegram that is still arriving from the independently clocked source.
	if (VoltagePacketBuildLength == 0 && (value & 0xC0U) != 0xC0U)
		return;

	VoltagePacketBuild[VoltagePacketBuildLength++] = value;
	if (VoltagePacketBuildLength == 6)
	{
		for (uint8_t index = 0; index < 6; index++)
			VoltagePacketPublished[index] = VoltagePacketBuild[index];
		__asm__ __volatile__("dmb sy" ::: "memory");
		VoltagePacketGeneration++;
		VoltagePacketBuildLength = 0;
	}
}

static bool decode_vue3_voltage_packet(void)
{
	uint8_t packet[6];
	// Most current scans need no work here. Copy a completed telegram only
	// when its generation changed; validation runs once per consumed telegram.
	const uint32_t primask = spi_enter_critical();
	const uint32_t generation = VoltagePacketGeneration;
	if (generation == VoltagePacketConsumedGeneration)
	{
		spi_exit_critical(primask);
		return VoltageValuesValid;
	}
	for (uint8_t index = 0; index < 6; index++)
		packet[index] = VoltagePacketPublished[index];
	VoltagePacketConsumedGeneration = generation;
	spi_exit_critical(primask);

	uint8_t phases_seen = 0;
	int16_t decoded[3] = {0, 0, 0};
	for (uint8_t pair = 0; pair < 3; pair++)
	{
		const uint8_t first = packet[pair * 2];
		const uint8_t second = packet[pair * 2 + 1];
		const uint8_t phase = second >> 6;
		if ((first & 0xC0U) != 0xC0U || phase >= 3 || (phases_seen & (1U << phase)) != 0)
		{
			VoltageRejectedTelegrams++;
			return VoltageValuesValid;
		}
		int16_t value = (int16_t) ((((uint16_t) first & 0x3FU) << 6) | (second & 0x3FU));
		if ((value & 0x0800) != 0)
			value = (int16_t) (value | 0xF000);
		decoded[phase] = value;
		phases_seen |= (uint8_t) (1U << phase);
	}
	if (phases_seen != 0x07)
	{
		VoltageRejectedTelegrams++;
		return VoltageValuesValid;
	}
	for (uint8_t phase = 0; phase < 3; phase++)
		DecodedVoltage[phase] = decoded[phase];
	VoltageValuesValid = true;
	VoltageTelegramUpdates++;
	VoltageAgeScans = 0;
	return true;
}
#endif

static void finish_spi_tx(void);
void adc_config(void);

static void prepare_adc_scan_start(void)
{
	// The logical first mux must match the GPIOs before conversions begin.
	REG_PORT_OUT = (REG_PORT_OUT & ~0x1030000UL) | outputpinTable[0];
	// The reference was just configured; the first conversion is not usable.
	DiscardNextAdcScan = true;
}

static void enable_adc_dma(void)
{
	if (dmabool == false)
	{
		dmabool = true;
		DMAdescriptor[DMA_CHANNEL_ADC].BTCNT = ADC_CHANNEL_COUNT;
		DMAdescriptor[DMA_CHANNEL_ADC].SRCADDR = (uint32_t) &REG_ADC_RESULT;//Source address
		DMAdescriptor[DMA_CHANNEL_ADC].DSTADDR =
			(uint32_t) &DMAresults[DMAresultIndex][ADC_CHANNEL_COUNT];
		// DMAC incrementing destinations use the address immediately after the block.
		DMAdescriptor[DMA_CHANNEL_ADC].DESCADDR = 0;
		__asm__ __volatile__("dmb sy" ::: "memory");
		REG_DMAC_CHID = DMA_CHANNEL_ADC;
		REG_DMAC_CHINTFLAG = DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND;
		REG_DMAC_CHCTRLA = DMA_CHANNEL_ENABLE;
	}
}

static void recover_adc_scan(void)
{
	// Overruns and partial/failed DMA blocks can lose the ADC pin-scan position.
	// Stop the trigger, reset the ADC sequence and discard the first complete
	// scan after re-enabling because the reference has just been configured.
	REG_TC1_CTRLA &= (uint16_t) ~2U;
	do {
	} while (REG_TC1_STATUS >= 0x80);

	REG_DMAC_CHID = DMA_CHANNEL_ADC;
	REG_DMAC_CHCTRLA = 0;
	REG_DMAC_CHINTFLAG = DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND;
	dmabool = false;

	REG_ADC_CTRLA &= (uint8_t) ~2U;
	do {
	} while ((REG_ADC_STATUS & STATUS_SYNCBUSY_BIT) != 0);
	adc_config();
	REG_ADC_INTFLAG = 0x0F;
	REG_TC1_INTFLAG = 0x3B;

	SpiBuildScanIndex = 0;
	DiscardNextAdcScan = true;
	enable_adc_dma();

	REG_ADC_CTRLA |= 2;
	do {
	} while ((REG_ADC_STATUS & STATUS_SYNCBUSY_BIT) != 0);
	REG_TC1_CTRLA |= 2;
	do {
	} while (REG_TC1_STATUS >= 0x80);
}

static void handle_adc_dma_interrupt(uint8_t flags)
{
	dmabool = false;
	const bool dma_error = (flags & (DMA_INT_TRANSFER_ERROR | DMA_INT_SUSPEND)) != 0 ||
		(flags & DMA_INT_TRANSFER_COMPLETE) == 0;
	const bool adc_overrun = (REG_ADC_INTFLAG & ADC_INTFLAG_OVERRUN) != 0;
	if (dma_error)
		SpiPendingFlags |= SPI_FLAG_DMA_ERROR;
	if (adc_overrun)
		SpiPendingFlags |= SPI_FLAG_ADC_OVERRUN;
	if (dma_error || adc_overrun)
	{
		// Rearming DMA alone could label the next ADC pin as channel zero.
		// Reset the complete scan before publishing any more sample blocks.
		recover_adc_scan();
		return;
	}

	const uint8_t lastindex = DMAresultIndex;
	DMAresultIndex = (uint8_t) ((DMAresultIndex + 1) % ADC_SCAN_BUFFER_COUNT);

	__asm__ __volatile__("dmb sy" ::: "memory");
	if (DiscardNextAdcScan)
	{
		DiscardNextAdcScan = false;
		enable_adc_dma();
		return;
	}

	const uint8_t Muxnr = MuxCounter;
	MuxCounter++;
	MuxCounter = MuxCounter & 7; //max 7

	REG_PORT_OUTSET = MUX_SWITCH_GUARD_PIN_MASK;
	REG_PORT_OUT = ((REG_PORT_OUT ^ outputpinTable[MuxCounter]) & 0x1030000) ^ REG_PORT_OUT; //0x1030000 = 00000001 00000011 00000000 00000000 = pins 16, 17, 24.

	enable_adc_dma();

#ifdef EMPORIAVUE_TARGET_VUE3
	if (VoltageValuesValid && VoltageAgeScans != 0xFFFFFFFFUL)
		VoltageAgeScans++;
	if (!decode_vue3_voltage_packet())
		SpiPendingFlags |= SPI_FLAG_VOLTAGE_ERROR;
#endif
	capture_spi_scan(lastindex, Muxnr);

	REG_PORT_OUTCLR = MUX_SWITCH_GUARD_PIN_MASK;
}

static void handle_spi_tx_dma_interrupt(uint8_t flags)
{
	if (!SpiTxActive)
	{
		SpiPendingFlags |= SPI_FLAG_DMA_ERROR;
		return;
	}

	if ((flags & DMA_INT_TRANSFER_ERROR) != 0 || (flags & DMA_INT_TRANSFER_COMPLETE) == 0)
	{
		SpiPendingFlags |= SPI_FLAG_DMA_ERROR;
		// A transfer error can happen before any byte reaches SERCOM, in which
		// case TXC would never be raised after it was cleared at frame start.
		// Abort the partial frame immediately; no register polling is needed.
		REG_DMAC_CHCTRLA = 0;
		SpiTxAwaitingComplete = true;
		finish_spi_tx();
		return;
	}

	// DMA completion only means that the final byte reached SERCOM DATA. The
	// lower-priority SERCOM interrupt releases CS after TXC confirms that the
	// byte has left the shift register.
	SpiTxAwaitingComplete = true;
	__asm__ __volatile__("dmb sy" ::: "memory");
	REG_SERCOM1_INTENSET = SERCOM_INT_TXC;
}

void irq_handler_dmac(void)
{
	// Several channels can become pending before this shared handler runs.
	// Drain all of them so an SPI completion can never hide an ADC completion.
	for (;;)
	{
		const uint32_t pending = REG_DMAC_INTSTATUS & DMA_CHANNEL_MASK;
		if (pending == 0)
			break;

		const uint8_t channel = (pending & (1UL << DMA_CHANNEL_ADC)) != 0
			? DMA_CHANNEL_ADC : DMA_CHANNEL_SPI_TX;
		REG_DMAC_CHID = channel;
		const uint8_t flags = REG_DMAC_CHINTFLAG &
			(DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND);
		if (flags == 0)
		{
			SpiPendingFlags |= SPI_FLAG_DMA_ERROR;
			REG_DMAC_CHINTFLAG = DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND;
			break;
		}
		REG_DMAC_CHINTFLAG = flags;

		if (channel == DMA_CHANNEL_ADC)
			handle_adc_dma_interrupt(flags);
		else
			handle_spi_tx_dma_interrupt(flags);
	}
}

void enableADC()
{
	REG_ADC_CTRLA = REG_ADC_CTRLA | 2;
	do {
	}   while ((REG_ADC_STATUS & STATUS_SYNCBUSY_BIT) != 0);
}

void enable_TC1()
{
	REG_TC1_CTRLA = REG_TC1_CTRLA | 2;
	do {
	} while (REG_TC1_STATUS >= 0x80); //We defined it as unsigned, checking for bit 7, SYNCBUSY.
}

static void spi_frame_guard_delay(void)
{
	for (uint8_t index = 0; index < 32; index++)
		__asm__ __volatile__("nop");
}

static void spi_frame_cs_assert(void)
{
	REG_PORT_OUTCLR = SPI_FRAME_CS_PIN_MASK;
	spi_frame_guard_delay();
}

static void spi_frame_cs_deassert(void)
{
	// Callers either observed TXC or explicitly abort the transfer. Release
	// CS promptly; CRC/setup work provides the next frame's idle-high time.
	REG_PORT_OUTSET = SPI_FRAME_CS_PIN_MASK;
}

static void finish_spi_tx(void)
{
	REG_SERCOM1_INTENCLR = SERCOM_INT_TXC;
	const bool transfer_complete = SpiTxActive && SpiTxAwaitingComplete;
	if (transfer_complete)
		spi_frame_cs_deassert();

	// Acknowledge/drain SERCOM only after ending the wire transaction. The
	// frame remains owned until the queue update below completes.
	REG_SERCOM1_INTFLAG = SERCOM_INT_TXC;
	if ((REG_SERCOM1_INTFLAG & SERCOM_INT_RXC) != 0)
		(void) REG_SERCOM1_DATA;

	if (!transfer_complete)
		return;

	const uint32_t primask = spi_enter_critical();
	if (SpiReadyCount != 0)
	{
		SpiReadyHead = (uint8_t) ((SpiReadyHead + 1) % SPI_READY_QUEUE_CAPACITY);
		SpiReadyCount--;
	}
	else
		SpiPendingFlags |= SPI_FLAG_DMA_ERROR;
	SpiTxAwaitingComplete = false;
	SpiTxActive = false;
	spi_exit_critical(primask);
	__asm__ __volatile__("dmb sy" ::: "memory");
}

void irq_handler_sercom1(void)
{
	if ((REG_SERCOM1_INTFLAG & SERCOM_INT_TXC) != 0)
		finish_spi_tx();
}

static void start_spi_dma_if_ready(void)
{
	if (SpiTxActive || SpiReadyCount == 0)
		return;

	const uint8_t frame_index = SpiReadyFrameIndex[SpiReadyHead];
	struct SpiRawFrame* frame = &SpiFrames[frame_index];
	const uint8_t* bytes = (const uint8_t*) frame;
	// Software CRC-32: about three times faster than feeding the DMAC CRC engine byte
	// by byte while interrupts take their share, so each frame is ready within its period.
	uint32_t crc = 0xFFFFFFFFUL;
	for (uint16_t index = 0; index < SPI_FRAME_SIZE - SPI_CRC_SIZE; index++)
		crc = Crc32Table[(crc ^ bytes[index]) & 0xFF] ^ (crc >> 8);
	frame->crc32 = crc ^ 0xFFFFFFFFUL;

	volatile struct DMAdescriptorType* descriptor = &DMAdescriptor[DMA_CHANNEL_SPI_TX];
	descriptor->BTCTRL = 0x409; // Valid, block interrupt, byte beats, incrementing source.
	descriptor->BTCNT = SPI_FRAME_SIZE;
	descriptor->SRCADDR = (uint32_t) bytes + SPI_FRAME_SIZE;
	descriptor->DSTADDR = (uint32_t) &REG_SERCOM1_DATA;
	descriptor->DESCADDR = 0;
	__asm__ __volatile__("dmb sy" ::: "memory");

	// Only main starts a transfer. With SpiTxActive clear, the ADC ISR may
	// append a ready frame but cannot remove or modify the selected head.
	// Keep SERCOM housekeeping and the CS setup delay interruptible so ADC
	// DMA can be rearmed promptly, even if it completes during this setup.
	REG_SERCOM1_INTENCLR = SERCOM_INT_TXC;
	REG_SERCOM1_INTFLAG = SERCOM_INT_TXC;
	if ((REG_SERCOM1_INTFLAG & SERCOM_INT_RXC) != 0)
		(void) REG_SERCOM1_DATA;
	spi_frame_cs_assert();

	// CHID is shared with the ADC ISR: select and access the SPI channel only
	// inside this short critical section, after all interruptible setup.
	const uint32_t primask = spi_enter_critical();
	REG_DMAC_CHID = DMA_CHANNEL_SPI_TX;
	const uint32_t spi_dma_mask = 1UL << DMA_CHANNEL_SPI_TX;
	if ((REG_DMAC_CHCTRLA & DMA_CHANNEL_ENABLE) != 0 ||
		((REG_DMAC_BUSYCH | REG_DMAC_PENDCH) & spi_dma_mask) != 0)
	{
		SpiPendingFlags |= SPI_FLAG_DMA_ERROR;
		spi_exit_critical(primask);
		spi_frame_cs_deassert();
		return;
	}

	REG_DMAC_CHINTFLAG = DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND;
	SpiTxAwaitingComplete = false;
	SpiTxActive = true;
	REG_DMAC_CHCTRLA = DMA_CHANNEL_ENABLE;
	spi_exit_critical(primask);
}

void COnfigSerCom1 ()
{
	REG_GCLK_CLKCTRL = 0x410F; // Clock Enable, GCLK1, GCLK_SERCOM1_CORE = 16 MHz.
	REG_SERCOM1_CTRLA = 1; // SWRST
	do {
	} while (REG_SERCOM1_SYNCBUSY != 0);

	REG_SERCOM1_BAUD = 0; // 16 MHz core clock / 2 = 8 MHz SPI.
	REG_SERCOM1_CTRLB = 0;
	do {
	} while (REG_SERCOM1_SYNCBUSY != 0);

	REG_SERCOM1_CTRLA = 0x0C; // SPI master, mode 0, MSB first, DO=PAD0(PA22), SCK=PAD1(PA23).
	REG_SERCOM1_CTRLA = REG_SERCOM1_CTRLA | 2; // ENABLE
	do {
	} while (REG_SERCOM1_SYNCBUSY != 0);
	REG_SERCOM1_INTENCLR = 0xFF;
	REG_SERCOM1_INTFLAG = SERCOM_INT_TXC;
}

#ifdef EMPORIAVUE_TARGET_VUE3
void ConfigSerCom0VoltageReceiver(void)
{
	// Reproduce the stock Vue 3 receiver configuration. The external voltage
	// controller is receive-only on SERCOM0 PAD0 (PA04).
	REG_GCLK_CLKCTRL = 0x400E; // GCLK0, GCLK_SERCOM0_CORE = 48 MHz.
	REG_SERCOM0_CTRLA = 1; // SWRST
	do {
	} while (REG_SERCOM0_SYNCBUSY != 0);

	REG_SERCOM0_BAUD = 0x6AAB;
	REG_SERCOM0_CTRLB = 0x00020000UL; // RXEN
	do {
	} while (REG_SERCOM0_SYNCBUSY != 0);

	REG_SERCOM0_CTRLA = 0x40414104UL; // USART internal clock, RX=PAD0, LSB first.
	REG_SERCOM0_CTRLA |= 2; // ENABLE
	do {
	} while (REG_SERCOM0_SYNCBUSY != 0);
	REG_SERCOM0_INTENSET = SERCOM_INT_RXC | SERCOM_INT_ERROR;
}
#endif

void configureNestedVectoredInterruptController ()
{
	__asm__ __volatile__("dmb sy");
	__asm__ __volatile__("CPSIE I");
	REG_NVIC_PRIO1 = (REG_NVIC_PRIO1 & 0xFF00FFFF) | 0x400000;
	REG_NVIC_SETENA = 0x40; //Enable interrupt: 01000000 = int 6 = our DMA IRQ.
#ifdef EMPORIAVUE_TARGET_VUE3
	REG_NVIC_SETENA = 0x200; // SERCOM0 voltage-controller receive interrupt.
#endif
	// SERCOM1 only releases CS after DMA completion. Keep it below the DMAC
	// handler so it cannot preempt ADC queue maintenance.
	REG_NVIC_PRIO2 = (REG_NVIC_PRIO2 & 0xFF00FFFF) | 0x800000;
	REG_NVIC_SETENA = 0x400; // Interrupt 10 = SERCOM1.
	REG_NVIC_PRIO3 = (REG_NVIC_PRIO3 & 0xFFFF00FF) | 0xC000;
	REG_NVIC_SETENA = 0x2000; //Enable interrupt: 00100000 00000000 = int 13, why ??
}

void configureDirectMemoryAccessController ()
{
	REG_DMAC_BASEADDR = (uint32_t) &DMAdescriptor[0];
	DMAdescriptor[DMA_CHANNEL_ADC].BTCTRL = 0x909; //0000 1001 0000 1001.  stepsize = 0, So next address = beatsize*1
					   //STEPSEL = 0, so DST
					   // DSTINC = 1, so auto increment destination
					   // SRCINC = 0, so no auto increment on source.
					   //Beatsize = 16 bit
					   // blockact = 1 = INT = Channel in normal operation and block interrupt
					   //Event Output Selection = 0, DISABLE, no event generation
					   //valid.
	DMAdescriptor[DMA_CHANNEL_SPI_TX].BTCTRL = 0x409; // Valid, block interrupt, byte beats, incrementing source.
	REG_DMAC_WRBADDR  = (uint32_t) &DMAdescriptorwriteback[0];
	REG_DMAC_PRICTRL0 = 0x81818181; // Enable round-robin scheduling within every priority level.
	REG_DMAC_CHID = DMA_CHANNEL_ADC;
	REG_DMAC_CHCTRLB = DMA_CHCTRLB_TRIGACT_BEAT | (DMA_TRIGGER_ADC_RESRDY << 8) |
		DMA_CHCTRLB_PRIORITY_CRITICAL;
					//Software Command: no action
					//Trigger action: BEAT. One trigger required for each beat transfer
					//Channel resume operation
					//Trigger source = ADC Result Ready Trigger
					//Channel priority level 0, above the SPI transmitter
					//Channel event generation is disabled.
					//Channel event action will not be executed on any incoming event.
					//Event Input Action = NO action
	REG_DMAC_CHINTENSET = DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND;

	REG_DMAC_CHID = DMA_CHANNEL_SPI_TX;
	REG_DMAC_CHCTRLB = DMA_CHCTRLB_TRIGACT_BEAT | (DMA_TRIGGER_SERCOM1_TX << 8) |
		DMA_CHCTRLB_PRIORITY_BACKGROUND;
	REG_DMAC_CHINTENSET = DMA_INT_TRANSFER_ERROR | DMA_INT_TRANSFER_COMPLETE | DMA_INT_SUSPEND;
	REG_DMAC_CTRL = 0xF02; //00001111 00000010 = Transfer requests for all Priority levels are handled. No CRC. DMA enable.
}

void config_PORT()
{
	REG_PORT_DIR = 0x83030000; // PA16, PA17, PA24, PA25 mux outputs plus PA31 FRAME/CS.
#ifdef EMPORIAVUE_TARGET_VUE3
	REG_PORT_OUT = SPI_FRAME_CS_PIN_MASK | 0x00C00000UL; // Match stock idle state on PA22/PA23.
	REG_PINCFG2 = 1;
	REG_PINCFG3 = 1;
	REG_PINCFG4 = 1; // SERCOM0 PAD0 receives the external voltage telegram on PA04.
	REG_PINCFG5 = 1;
	REG_PINCFG7 = 1;
	REG_PINCFG8 = 4;
	REG_PINCFG9 = 4;
	REG_PINCFG10 = 4;
	REG_PINCFG11 = 4;
	REG_PINCFG15 = 1;
	REG_PINCFG22 = 5;
	REG_PINCFG23 = 5;
	REG_PINCFG25 = 4;
	REG_PINCFG27 = 4;
	REG_PINCFG28 = 4;
	REG_PINCFG30 = 4;
	REG_PINCFG31 = 0;
	REG_PORT_PMUX1 = 0x11;
	REG_PORT_PMUX2 = 0x13;
	REG_PORT_PMUX3 = 0x10;
	REG_PORT_PMUX5 = 0x11;
	REG_PORT_PMUX7 = 0x10;
	REG_PORT_PMUX11 = 0x22;
	REG_PORT_DIRSET = 0x400UL; // Match stock Vue 3: PA10 is a low output.
#else
	REG_PORT_OUT = SPI_FRAME_CS_PIN_MASK; // FRAME/CS idle high, rest driven low.
	REG_PINCFG2 = 1;
	REG_PINCFG3 = 1;
	REG_PINCFG4 = 1;
	REG_PINCFG5 = 1;
	REG_PINCFG6 = 1;
	REG_PINCFG7 = 1;
	REG_PINCFG8 = 4;
	REG_PINCFG9 = 4;
	REG_PINCFG10 = 1;
	REG_PINCFG11 = 1;
	REG_PINCFG14 = 1;
	REG_PINCFG15 = 1;
	REG_PINCFG22 = 5;
	REG_PINCFG23 = 5;
	REG_PINCFG25 = 4;
	REG_PINCFG27 = 4;
	REG_PINCFG28 = 4;
	REG_PINCFG31 = 0;
	// PA30/SWCLK and reset stay untouched so connect-under-reset remains available.
	REG_PORT_PMUX1 = 0x11;
	REG_PORT_PMUX2 = 0x11;
	REG_PORT_PMUX3 = 0x11;
	REG_PORT_PMUX5 = 0x11;
	REG_PORT_PMUX7 = 0x11;
	REG_PORT_PMUX11 = 0x22;
#endif
}

void ConfigureTimerCounter1 () {
	REG_TC1_CTRLA = 1; //SWRST
	do {
	} while (REG_TC1_STATUS >= 0x80); //We defined it as unsigned, checking for bit 7, SYNCBUSY.

	REG_TC1_CTRLA = 0x60; //0110 0000 Match PWM, 16 bit mode
	REG_TC1_COUNT16_CC0 = TC1_ADC_TRIGGER_PERIOD; //The period.
	REG_TC1_INTFLAG = 0x3B; //clear flags
	REG_TC1_EVCTRL = 0x100; // bit 8 = Overflow/Underflow event is enabled and will be generated for every counter overflow/underflow.
	do {
	} while (REG_TC1_STATUS >= 0x80); //We defined it as unsigned, checking for bit 7, SYNCBUSY.
}

void Config_NVMCTRL ()
{
	// MANW=1, RWS=1, SLEEPPRM=WAKEONACCESS. Allow Flash to sleep; the SRAM
	// wake-up sequence restores Flash access before unmasking interrupts.
	// Keep SPI setup interruptible so ADC DMA rearming is not delayed there.
	REG_NVMCTRL_CTRLB = 0x82;
}

void config_EventSystem ()
{
	REG_EVSYS_USER = 0x10C; //0001 00001100 connect channel 0, ADC_START as Event user
	REG_EVSYS_CHANNEL = 0x61F0000; // 0000 0110 0001 1111 00000000 00000000, EVGEN: 00011111 = TC1 OVF = TC1 underflow/overflow
}

void config_Sysctrl_PM_and_GCLK ()
{
	REG_SYSCTRL_OSC32K = 0;
	REG_SYSCTRL_DFLLCTRL = REG_SYSCTRL_DFLLCTRL & 0xFF7F; // & 1111111101111111 = The oscillator is always on, if enabled.
	do {
	} while ((REG_SYSCTRL_PCLKSR & 0x10) == 0); //DFLLRDY. Wait for oscillator stabilization

	uint32_t calibdat = *((uint32_t*)0x806024) >> 0x1a;
	if (calibdat == 0x3f)
		calibdat = 0x1f;

	calibdat = calibdat << 10;
	REG_SYSCTRL_DFLLVAL = calibdat | *((uint32_t*)0x806028) & 0x3ff;
	REG_SYSCTRL_DFLLCTRL = 2; //The DFLL oscillator is enabled.

	do {
	} while ((REG_SYSCTRL_PCLKSR & 0x10) == 0); //DFLLRDY. Wait for oscillator stabilization

	REG_GCLK_GENCTRL = 0x10700; //0000 0001 - 0000 0111 - 0000 0000 GCLKGEN0. Source  = DFLL48M output. The generic clock generator is enabled

	do {
	} while ((REG_GCLK_STATUS & STATUS_SYNCBUSY_BIT) != 0);

	REG_GCLK_GENCTRL = 0x30701; //0000 0011 - 0000 0111 - 0000 0001 GCLKGEN1. Source = DFLL48M output. The generic clock generator is enabled
	REG_GCLK_GENDIV = 0x301; //0000 0011 0000 0001. GCLKGEN1 3 division bits.

	do {
	} while ((REG_GCLK_STATUS & STATUS_SYNCBUSY_BIT) != 0);

	REG_GCLK_CLKCTRL = 0x4007; //0100 0000 0000 0111, enable GCLK0 EVSYS_CHANNEL_0
#ifdef EMPORIAVUE_TARGET_VUE3
	REG_GCLK_CLKCTRL = 0x400E; // enable GCLK0 SERCOM0_CORE
#endif
	REG_GCLK_CLKCTRL = 0x410F; //0100 0001 0000 1111, enable GCLK1 SERCOM1_CORE
	REG_GCLK_CLKCTRL = 0x4112; //0100 0001 0001 0010, enable GCLK1 TC2
	REG_GCLK_CLKCTRL = 0x4113; //0100 0001 0001 0011, enable GCLK1 ADC

#ifdef EMPORIAVUE_TARGET_VUE3
	REG_PM_APBCMASK = 0x14E; // enable ADC, TC1, SERCOM0 and SERCOM1
#else
	REG_PM_APBCMASK = 0x14A; // enable ADC, TC1 and SERCOM1
#endif
	REG_SYSCTRL_OSC8M = 0;
}

void adc_config() {

	REG_ADC_CTRLA = 1; //SWRST: Writing a one to this bit resets all registers in the ADC,to their initial state, and the ADC will be disabled
	do {
	}   while ((REG_ADC_STATUS & STATUS_SYNCBUSY_BIT) != 0);

        //Load ADC factory calibration values
	uint32_t tmp =  (*((uint32_t*)0x806024) << 5) & 0x700 | *((uint32_t*)0x806020) >> 27 | (*((uint32_t*)0x806024) << 5) & 0xff | ((*((uint32_t*)0x806024) & 7) << 5);
	REG_ADC_CALIB = tmp;
	REG_ADC_SAMPCTRL = ADC_SAMPLE_TIME_LENGTH; //Sampling Time Length
	REG_ADC_REFCTRL = ADC_REFCTRL_VREFA; //VREFA as reference
	REG_ADC_INPUTCTRL = ADC_INPUTCTRL_SCAN_DIFF_GAIN2;
#ifdef EMPORIAVUE_TARGET_VUE3
					// Vue 3: gain 2X, input offset 3, scan count 5 = AIN3..AIN7.
#else
					//  00000001 = GAIN 2X.
					// 0010  =inputoffset: 2.
					// 0111 = Inputscan= 7+1 = 8
#endif
	REG_ADC_CTRLB = ADC_CTRLB_DIV8_12BIT_DIFF; //0000 0001 0000 0001
				//ADC clock : Peripheral clock = 1 : 8
				//12 bits conversion
				//Disable digital result correction
				//The ADC conversion result is right-adjusted in the RESULT register.
				//Single conversion mode
				//Differential mode. In this mode, the voltage difference between the MUXPOS and MUXNEG inputs will be converted by the ADC
	REG_ADC_INTFLAG = 0xF; //clear intflags
	REG_ADC_EVCTRL = 1; //A new conversion will be triggered on any incoming event
	do {
	}  while ((REG_ADC_STATUS & STATUS_SYNCBUSY_BIT) != 0);
}

int main(void)
{
	set_boot_stage(BOOT_STAGE_MAIN_ENTRY);
	REG_NVMCTRL_CTRLB = 6;
	set_boot_stage(BOOT_STAGE_NVM_READ_WAIT);

	config_PORT();
	set_boot_stage(BOOT_STAGE_PORT_CONFIGURED);
	config_Sysctrl_PM_and_GCLK ();
	configure_idle_sleep();
	set_boot_stage(BOOT_STAGE_CLOCK_CONFIGURED);
	Config_NVMCTRL();
	set_boot_stage(BOOT_STAGE_NVM_MANUAL_WRITE);
	config_EventSystem();
	set_boot_stage(BOOT_STAGE_EVENT_SYSTEM_CONFIGURED);
#ifdef EMPORIAVUE_TARGET_VUE3
	ConfigSerCom0VoltageReceiver();
	set_boot_stage(BOOT_STAGE_SERCOM0_CONFIGURED);
#endif
	configureDirectMemoryAccessController();
	set_boot_stage(BOOT_STAGE_DMAC_CONFIGURED);
	adc_config();
	set_boot_stage(BOOT_STAGE_ADC_CONFIGURED);
	ConfigureTimerCounter1 ();
	set_boot_stage(BOOT_STAGE_TC1_CONFIGURED);
	configureNestedVectoredInterruptController();
	set_boot_stage(BOOT_STAGE_NVIC_CONFIGURED);
	prepare_adc_scan_start();
	enable_adc_dma();
	set_boot_stage(BOOT_STAGE_DMA_ENABLED);
	enableADC ();
	set_boot_stage(BOOT_STAGE_ADC_ENABLED);
	enable_TC1();
	set_boot_stage(BOOT_STAGE_TC1_ENABLED);
	COnfigSerCom1();
	set_boot_stage(BOOT_STAGE_SERCOM1_CONFIGURED);

	set_boot_stage(BOOT_STAGE_MAIN_LOOP);
	for (;;) //main program loop
	{
		start_spi_dma_if_ready();
		wait_for_spi_work();
	}
	return 0;
}
